"""Routes an incoming chat turn to the right skill, retrieves grounding
context, calls the resolved LLM provider, and returns a uniform result the
API layer can persist and serialize."""

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.skills import artifact_skill, qa_skill, ship30_skill, smalltalk_skill
from app.artifacts.sanitize import sanitize_html_artifact
from app.core.config import get_settings
from app.llm import claude_agent_provider
from app.llm.base import ChatTurn, ProviderTimeoutError, ProviderUnavailableError
from app.llm.registry import resolve_provider
from app.rag.retrieval import retrieve, to_citations

logger = logging.getLogger(__name__)

SHIP30_TRIGGERS = ["ship 30", "ship30", "atomic essay", "turn this into an essay", "write an essay"]

# Phrases that identify a skill request but carry no topical signal for
# retrieval. Postgres's ts_rank normalizes against how many of the query's
# lexemes actually matched, so a verbose request like "Write a Ship 30 essay
# on onboarding" scores *lower* than the bare topic "onboarding" alone --
# measured on this corpus: 0.027 (below the 0.03 relevance floor) vs. 0.083.
# Stripped only for the ship30/artifact skills, which route their raw request
# text into the same query used to decide "not grounded" -- qa_skill's
# retrieval (and its regression tests) are untouched by this.
_RETRIEVAL_BOILERPLATE = [
    "write a", "write an", "write", "generate", "create", "produce", "draft",
    "render this as", "turn this into", "summarizing", "summarize", "essay",
]


def _retrieval_query(message: str) -> str:
    """Strip skill-invocation boilerplate so retrieval scores the topic, not
    the request phrasing around it. Falls back to the original message if
    stripping would leave nothing to search on."""
    lowered = message.lower()
    for phrase in (*SHIP30_TRIGGERS, *artifact_skill.HTML_TRIGGERS, *artifact_skill.MARKDOWN_TRIGGERS, *_RETRIEVAL_BOILERPLATE):
        lowered = lowered.replace(phrase, " ")
    cleaned = " ".join(lowered.split())
    return cleaned if cleaned else message


@dataclass
class AgentResponse:
    text: str
    skill: str
    provider: str
    model: str
    grounded: bool | None
    fell_back: bool
    citations: list[dict]
    artifact: dict | None


def _detect_skill(message: str, requested_skill: str | None) -> str:
    if requested_skill in ("qa", "ship30", "artifact"):
        return requested_skill
    if artifact_skill.detect_artifact_format(message):
        return "artifact"
    if any(trigger in message.lower() for trigger in SHIP30_TRIGGERS):
        return "ship30"
    return "qa"


async def run_turn(
    db: AsyncSession,
    user_message: str,
    history: list[ChatTurn],
    requested_skill: str | None = None,
    requested_artifact_format: str | None = None,
) -> AgentResponse:
    # Checked before skill routing and before resolving a provider at all --
    # a greeting needs neither retrieval nor an LLM call, and only fires when
    # the client didn't explicitly request a skill (an explicit "ship30"/
    # "artifact" request is respected even if its text happens to be short).
    if requested_skill is None:
        smalltalk_response = smalltalk_skill.detect(user_message)
        if smalltalk_response is not None:
            return AgentResponse(
                text=smalltalk_response,
                skill="smalltalk",
                provider="",
                model="",
                grounded=False,
                fell_back=False,
                citations=[],
                artifact=None,
            )

    settings = get_settings()
    skill = _detect_skill(user_message, requested_skill)
    resolved = await resolve_provider()
    provider = resolved.provider

    # Bind this request's DB session to the Claude Agent SDK's retrieval tool.
    # Each request runs in its own asyncio task, so the ContextVar set here is
    # scoped to this turn and can't leak into a concurrent one. No-op for the
    # providers that don't use SDK tool-calling.
    async def _tool_retrieve(query: str):
        return await retrieve(
            db, query, top_k=settings.retrieval_top_k, min_rank=settings.retrieval_min_rank
        )

    claude_agent_provider.set_retriever(_tool_retrieve)

    if skill == "artifact":
        fmt = requested_artifact_format or artifact_skill.detect_artifact_format(user_message) or "markdown"
        chunks = await retrieve(
            db,
            _retrieval_query(user_message),
            top_k=settings.retrieval_top_k,
            min_rank=settings.retrieval_min_rank,
        )
        system_prompt = artifact_skill.build_system_prompt(fmt, chunks)
        try:
            result = await provider.complete(system_prompt, history, user_message, max_tokens=2500)
        except ProviderUnavailableError as exc:
            return _error_response(
                skill, provider.name, str(exc), timed_out=isinstance(exc, ProviderTimeoutError)
            )

        content = artifact_skill.extract_artifact_content(result.text)
        if fmt == "html":
            content = sanitize_html_artifact(content)

        return AgentResponse(
            text=f"Generated a {fmt.upper()} artifact -- see the Artifact Viewer.",
            skill=skill,
            provider=result.provider,
            model=result.model,
            grounded=bool(chunks),
            fell_back=resolved.fell_back,
            citations=to_citations(chunks),
            artifact={"format": fmt, "content": content},
        )

    if skill == "ship30":
        chunks = await retrieve(
            db,
            _retrieval_query(user_message),
            top_k=settings.retrieval_top_k,
            min_rank=settings.retrieval_min_rank,
        )
        system_prompt = ship30_skill.build_system_prompt(user_message, chunks)
        try:
            result = await provider.complete(
                system_prompt,
                history,
                user_message,
                max_tokens=3000,
                timeout_override=settings.ollama_ship30_timeout_seconds,
            )

            # No grounding chunks means the model was told to refuse, not to
            # write an essay -- retrying or requirement-checking that refusal
            # would only pressure it into padding/fabricating content to meet
            # requirements it was never supposed to meet.
            if chunks:
                # A draft can violate the rubric's hard requirements in ways
                # word count alone never catches -- reproduced live: a
                # 1,081-word essay (within tolerance) that used zero `## `
                # headings and `### The Takeaway` instead of `## `. One retry
                # pass fires on *any* violation, not just under-length.
                original_issues = ship30_skill.draft_issues(result.text)
                if original_issues:
                    logger.info(
                        "ship30_retrying_draft",
                        extra={
                            "event": "ship30_retrying_draft",
                            "provider": result.provider,
                            "model": result.model,
                            "error": "; ".join(original_issues),
                        },
                    )
                    expanded = await provider.complete(
                        system_prompt,
                        [],
                        ship30_skill.build_expansion_prompt(result.text, original_issues),
                        max_tokens=4000,
                        timeout_override=settings.ollama_ship30_timeout_seconds,
                    )
                    expanded_issues = ship30_skill.draft_issues(expanded.text)
                    # Only accept the retry if it actually improved things --
                    # fewer unmet requirements, or the same count but longer
                    # (a model that came back shorter with no other fix has
                    # just ignored the ask).
                    if len(expanded_issues) < len(original_issues) or (
                        len(expanded_issues) == len(original_issues)
                        and len(expanded.text.split()) > len(result.text.split())
                    ):
                        result = expanded
        except ProviderUnavailableError as exc:
            return _error_response(
                skill, provider.name, str(exc), timed_out=isinstance(exc, ProviderTimeoutError)
            )

        if chunks:
            remaining_issues = ship30_skill.draft_issues(result.text)
            if remaining_issues:
                logger.info(
                    "ship30_requirements_unmet",
                    extra={
                        "event": "ship30_requirements_unmet",
                        "error": "; ".join(remaining_issues),
                    },
                )

        return AgentResponse(
            text=result.text,
            skill=skill,
            provider=result.provider,
            model=result.model,
            grounded=bool(chunks),
            fell_back=resolved.fell_back,
            citations=to_citations(chunks),
            artifact=None,
        )

    # default: grounded Q&A
    chunks = await retrieve(
        db,
        user_message,
        top_k=settings.retrieval_top_k,
        min_rank=settings.retrieval_min_rank,
    )
    system_prompt = qa_skill.build_system_prompt(chunks)
    try:
        result = await provider.complete(system_prompt, history, user_message)
    except ProviderUnavailableError as exc:
        return _error_response(
            skill, provider.name, str(exc), timed_out=isinstance(exc, ProviderTimeoutError)
        )

    return AgentResponse(
        text=result.text,
        skill=skill,
        provider=result.provider,
        model=result.model,
        grounded=bool(chunks),
        fell_back=resolved.fell_back,
        citations=to_citations(chunks),
        artifact=None,
    )


def _error_response(
    skill: str, provider_name: str, message: str, timed_out: bool = False
) -> AgentResponse:
    logger.error(
        "provider_error",
        extra={"event": "provider_error", "provider": provider_name, "error": message},
    )
    if timed_out:
        user_text = (
            f"That took longer than {provider_name} was given to answer, so I stopped waiting. "
            "Long essay-length generations are slow on CPU-only hardware -- try a shorter request, "
            "raise OLLAMA_TIMEOUT_SECONDS, or switch to a smaller model or a cloud provider."
        )
    else:
        user_text = (
            "I couldn't reach the language model to answer that. "
            f"({provider_name} is currently unavailable.) Try again in a moment, or switch providers "
            "in settings."
        )
    return AgentResponse(
        text=user_text,
        skill=skill,
        provider=provider_name,
        model="",
        grounded=None,
        fell_back=False,
        citations=[],
        artifact=None,
    )
