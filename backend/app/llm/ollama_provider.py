import logging

import httpx

from app.llm.base import (
    ChatTurn,
    LLMProvider,
    ProviderResult,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """The mandatory local-model path. Talks to a locally running Ollama daemon."""

    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout_seconds: float = 600.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def complete(
        self,
        system_prompt: str,
        history: list[ChatTurn],
        user_message: str,
        max_tokens: int = 1500,
    ) -> ProviderResult:
        messages = [{"role": "system", "content": system_prompt}]
        messages += [{"role": t.role, "content": t.content} for t in history]
        messages.append({"role": "user", "content": user_message})

        try:
            # Local models can take 30-60s+ to cold-load into memory on modest
            # hardware before any generation even starts (observed ~50s for
            # llama3.1 during this build) -- a short timeout here reads as a
            # false "provider unavailable" for what's really just a slow but
            # working load. A long Ship 30 essay (~1,250 words) is far slower
            # still: 300s was not enough on CPU-only hardware and surfaced as a
            # bogus "Ollama is unavailable" error, hence the generous default.
            # keep_alive keeps the model resident between turns so only the
            # *first* message in a while pays the load cost.
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "keep_alive": "30m",
                        "options": {"num_predict": max_tokens},
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException as exc:
            # str() on an httpx timeout is empty, so log the exception *type* or
            # the operator gets `"error": ""` and cannot tell a slow model from
            # a refused connection.
            logger.warning(
                "ollama_request_timeout",
                extra={
                    "event": "ollama_request_timeout",
                    "error": f"{type(exc).__name__} after {self.timeout_seconds}s",
                    "model": self.model,
                },
            )
            raise ProviderTimeoutError(
                f"Ollama did not respond within {self.timeout_seconds:.0f}s "
                f"(model: {self.model}). Long generations on CPU-only hardware can exceed this; "
                "raise OLLAMA_TIMEOUT_SECONDS or use a smaller model."
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning(
                "ollama_request_failed",
                extra={
                    "event": "ollama_request_failed",
                    "error": f"{type(exc).__name__}: {exc}",
                    "model": self.model,
                },
            )
            raise ProviderUnavailableError(f"Ollama request failed: {type(exc).__name__}: {exc}") from exc

        text = data.get("message", {}).get("content", "").strip()
        if not text:
            raise ProviderUnavailableError("Ollama returned an empty response")

        return ProviderResult(text=text, provider=self.name, model=self.model)
