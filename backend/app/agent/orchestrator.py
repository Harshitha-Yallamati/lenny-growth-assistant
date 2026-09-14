"""Routes an incoming chat turn to the right skill, retrieves grounding
context, calls the resolved LLM provider, and returns a uniform result the
API layer can persist and serialize."""

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.skills import artifact_skill, qa_skill, ship30_skill
from app.artifacts.sanitize import sanitize_html_artifact
from app.core.config import get_settings
from app.llm.base import ChatTurn, ProviderUnavailableError
from app.llm.registry import resolve_provider
from app.rag.retrieval import retrieve, to_citations

logger = logging.getLogger(__name__)

SHIP30_TRIGGERS = ["ship 30", "ship30", "atomic essay", "turn this into an essay", "write an essay"]


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
    settings = get_settings()
    skill = _detect_skill(user_message, requested_skill)
    resolved = await resolve_provider()
    provider = resolved.provider

    if skill == "artifact":
        fmt = requested_artifact_format or artifact_skill.detect_artifact_format(user_message) or "markdown"
        chunks = await retrieve(db, user_message, top_k=settings.retrieval_top_k)
        system_prompt = artifact_skill.build_system_prompt(fmt, chunks)
        try:
            result = await provider.complete(system_prompt, history, user_message, max_tokens=2500)
        except ProviderUnavailableError as exc:
            return _error_response(skill, provider.name, str(exc))

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
        chunks = await retrieve(db, user_message, top_k=settings.retrieval_top_k)
        system_prompt = ship30_skill.build_system_prompt(user_message, chunks)
        try:
            result = await provider.complete(system_prompt, history, user_message, max_tokens=3000)
        except ProviderUnavailableError as exc:
            return _error_response(skill, provider.name, str(exc))

        if not ship30_skill.word_count_within_tolerance(result.text):
            logger.info("ship30_word_count_out_of_range", extra={"event": "ship30_word_count_out_of_range"})

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
    chunks = await retrieve(db, user_message, top_k=settings.retrieval_top_k)
    system_prompt = qa_skill.build_system_prompt(chunks)
    try:
        result = await provider.complete(system_prompt, history, user_message)
    except ProviderUnavailableError as exc:
        return _error_response(skill, provider.name, str(exc))

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


def _error_response(skill: str, provider_name: str, message: str) -> AgentResponse:
    logger.error("provider_error", extra={"event": "provider_error", "provider": provider_name})
    return AgentResponse(
        text=(
            "I couldn't reach the language model to answer that. "
            f"({provider_name} is currently unavailable.) Try again in a moment, or switch providers "
            "in settings."
        ),
        skill=skill,
        provider=provider_name,
        model="",
        grounded=None,
        fell_back=False,
        citations=[],
        artifact=None,
    )
