"""Anthropic path built on the **Claude Agent SDK** (`claude-agent-sdk`).

This satisfies the assignment's §3.1 requirement that the agent layer be built
with the Claude Agent SDK. Two properties of that SDK shape everything here:

1. It is Claude Code packaged as a library -- it drives the `claude` CLI as a
   subprocess, so the runtime needs Node.js plus `@anthropic-ai/claude-code`
   (installed in the backend image). If either is missing we report
   unavailable rather than raising, and the registry degrades to the native
   Messages API and then to Ollama.

2. It ships built-in Read/Write/Edit/Bash/Glob/Grep tools. Handing those to a
   model inside a web backend would give it shell and filesystem access on the
   server, so `allowed_tools` below is a strict allow-list naming **only** our
   retrieval tool. Nothing else is granted.

Retrieval is exposed as a genuine SDK tool (`@tool` + `create_sdk_mcp_server`)
so the agent can search the transcripts itself. The orchestrator still
pre-retrieves and injects context into the system prompt exactly as it does
for the other providers, so grounding and citations behave identically no
matter which provider is active; the tool is additive, for when the agent
wants to dig further.
"""

import logging
import shutil
from contextvars import ContextVar
from typing import Any

from app.llm.base import ChatTurn, LLMProvider, ProviderResult, ProviderUnavailableError

logger = logging.getLogger(__name__)

# The retrieval tool runs inside the SDK's own callback, which has no access to
# the request-scoped DB session. A ContextVar set in complete() bridges that
# gap without turning the DB session into global state.
_retriever: ContextVar[Any | None] = ContextVar("agent_sdk_retriever", default=None)

TOOL_SERVER_NAME = "lenny_kb"
TOOL_NAME = "search_transcripts"
QUALIFIED_TOOL = f"mcp__{TOOL_SERVER_NAME}__{TOOL_NAME}"


def sdk_available() -> bool:
    """True only if both halves of the SDK's runtime contract are present."""
    try:
        import claude_agent_sdk  # noqa: F401
    except ImportError:
        return False
    return shutil.which("claude") is not None


def _build_tool_server():
    """Build the in-process MCP server exposing transcript search to the agent.

    Imported lazily so the module stays importable when the SDK isn't
    installed -- the backend must boot fine without it.
    """
    from claude_agent_sdk import create_sdk_mcp_server, tool

    @tool(TOOL_NAME, "Search Lenny's Podcast transcripts for relevant excerpts", {"query": str})
    async def search_transcripts(args: dict[str, Any]) -> dict[str, Any]:
        retriever = _retriever.get()
        if retriever is None:
            return {"content": [{"type": "text", "text": "Transcript search is unavailable."}]}

        chunks = await retriever(args["query"])
        if not chunks:
            return {
                "content": [
                    {"type": "text", "text": "No transcript excerpts matched that query."}
                ]
            }

        rendered = "\n\n---\n\n".join(
            f"[Source: {c.source_title}]\n{c.content}" for c in chunks
        )
        return {"content": [{"type": "text", "text": rendered}]}

    return create_sdk_mcp_server(
        name=TOOL_SERVER_NAME, version="1.0.0", tools=[search_transcripts]
    )


def _flatten_history(history: list[ChatTurn], user_message: str) -> str:
    """Render prior turns into the prompt.

    Our sessions live in Postgres, so each call is stateless from the SDK's
    point of view -- we don't use `continue_conversation`/`resume`, which would
    put session state in the CLI's own store and split the source of truth.
    """
    if not history:
        return user_message
    transcript = "\n\n".join(
        f"{'User' if t.role == 'user' else 'Assistant'}: {t.content}" for t in history
    )
    return f"Conversation so far:\n{transcript}\n\nUser: {user_message}"


class ClaudeAgentSDKProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str, max_turns: int = 6):
        self.api_key = api_key
        self.model = model
        self.max_turns = max_turns
        self._server = None

    async def is_available(self) -> bool:
        return bool(self.api_key) and sdk_available()

    async def complete(
        self,
        system_prompt: str,
        history: list[ChatTurn],
        user_message: str,
        max_tokens: int = 1500,
        timeout_override: float | None = None,
    ) -> ProviderResult:
        if not self.api_key:
            raise ProviderUnavailableError("ANTHROPIC_API_KEY is not configured")
        if not sdk_available():
            raise ProviderUnavailableError(
                "claude-agent-sdk requires the Claude Code CLI on PATH "
                "(npm i -g @anthropic-ai/claude-code)"
            )

        from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

        if self._server is None:
            self._server = _build_tool_server()

        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            model=self.model,
            mcp_servers={TOOL_SERVER_NAME: self._server},
            # Strict allow-list: the agent gets transcript search and nothing
            # else. No Bash, no file read/write -- see module docstring.
            allowed_tools=[QUALIFIED_TOOL],
            max_turns=self.max_turns,
        )

        parts: list[str] = []
        try:
            async for message in query(
                prompt=_flatten_history(history, user_message), options=options
            ):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            parts.append(block.text)
        except Exception as exc:  # the SDK raises transport/CLI errors of its own
            logger.warning(
                "claude_agent_sdk_failed",
                extra={
                    "event": "claude_agent_sdk_failed",
                    "error": f"{type(exc).__name__}: {exc}",
                    "model": self.model,
                },
            )
            raise ProviderUnavailableError(
                f"Claude Agent SDK request failed: {type(exc).__name__}: {exc}"
            ) from exc

        text = "".join(parts).strip()
        if not text:
            raise ProviderUnavailableError("Claude Agent SDK returned an empty response")

        return ProviderResult(text=text, provider=self.name, model=self.model)


def set_retriever(fn) -> object:
    """Install the request-scoped retrieval callback; returns a reset token."""
    return _retriever.set(fn)


def reset_retriever(token) -> None:
    _retriever.reset(token)
