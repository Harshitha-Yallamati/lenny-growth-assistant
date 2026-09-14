import logging

import openai

from app.llm.base import ChatTurn, LLMProvider, ProviderResult, ProviderUnavailableError

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self._client = openai.AsyncOpenAI(api_key=api_key) if api_key else None

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
            raise ProviderUnavailableError("OPENAI_API_KEY is not configured")

        messages = [{"role": "system", "content": system_prompt}]
        messages += [{"role": t.role, "content": t.content} for t in history]
        messages.append({"role": "user", "content": user_message})

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
            )
        except openai.OpenAIError as exc:
            logger.warning("openai_request_failed", extra={"event": "openai_request_failed"})
            raise ProviderUnavailableError(f"OpenAI request failed: {exc}") from exc

        text = (response.choices[0].message.content or "").strip()
        if not text:
            raise ProviderUnavailableError("OpenAI returned an empty response")

        return ProviderResult(text=text, provider=self.name, model=self.model)
