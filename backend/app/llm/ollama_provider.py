import logging

import httpx

from app.llm.base import ChatTurn, LLMProvider, ProviderResult, ProviderUnavailableError

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """The mandatory local-model path. Talks to a locally running Ollama daemon."""

    name = "ollama"

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

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
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {"num_predict": max_tokens},
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("ollama_request_failed", extra={"event": "ollama_request_failed"})
            raise ProviderUnavailableError(f"Ollama request failed: {exc}") from exc

        text = data.get("message", {}).get("content", "").strip()
        if not text:
            raise ProviderUnavailableError("Ollama returned an empty response")

        return ProviderResult(text=text, provider=self.name, model=self.model)
