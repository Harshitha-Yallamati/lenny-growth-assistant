"""Cloud provider backed by Anthropic's Messages API.

Design note (documented in architecture.md): the assignment allows either the
Claude Agent SDK or the Pi Coding Agent for the agent layer. The Agent SDK
shells out to the Claude Code CLI over a Node.js subprocess, which would mean
bundling a Node runtime into this Python backend's Docker image solely to
serve an *optional* cloud path we can't even test here (no API key was
available during this build) -- while Ollama is the mandatory, primary demo
path. Instead we implement the same agentic pattern (system prompt + tool-use
loop) directly against Anthropic's native Messages API, which is the lower-
level primitive the Agent SDK itself wraps. This keeps the image small and
this path fully debuggable without a CLI subprocess, at the cost of not
literally depending on the `claude-agent-sdk` package.
"""

import logging

import anthropic

from app.llm.base import ChatTurn, LLMProvider, ProviderResult, ProviderUnavailableError

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key) if api_key else None

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def complete(
        self,
        system_prompt: str,
        history: list[ChatTurn],
        user_message: str,
        max_tokens: int = 1500,
    ) -> ProviderResult:
        if not self._client:
            raise ProviderUnavailableError("ANTHROPIC_API_KEY is not configured")

        messages = [{"role": t.role, "content": t.content} for t in history]
        messages.append({"role": "user", "content": user_message})

        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
            )
        except anthropic.APIError as exc:
            logger.warning("anthropic_request_failed", extra={"event": "anthropic_request_failed"})
            raise ProviderUnavailableError(f"Anthropic request failed: {exc}") from exc

        text_parts = [block.text for block in response.content if block.type == "text"]
        text = "".join(text_parts).strip()
        if not text:
            raise ProviderUnavailableError("Anthropic returned an empty response")

        return ProviderResult(text=text, provider=self.name, model=self.model)
