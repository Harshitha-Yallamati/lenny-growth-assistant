from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ChatTurn:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class ProviderResult:
    text: str
    provider: str
    model: str


class ProviderUnavailableError(RuntimeError):
    """Raised when a provider cannot serve a request (missing key, network down)."""


class ProviderTimeoutError(ProviderUnavailableError):
    """The provider is reachable but didn't finish in time.

    Distinct from ProviderUnavailableError so the user isn't told the model is
    "unavailable" when it's actually up and merely slow -- that sends people
    restarting a healthy Ollama instead of waiting or picking a smaller model.
    """


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def is_available(self) -> bool:
        """Cheap reachability/config check used by /health and provider fallback."""

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        history: list[ChatTurn],
        user_message: str,
        max_tokens: int = 1500,
        timeout_override: float | None = None,
    ) -> ProviderResult:
        """Run one turn of chat completion. Raises ProviderUnavailableError on failure.

        timeout_override: use this timeout instead of the provider's default
        for this call only (e.g. Ship 30's long-form generation needs more
        time than an ordinary QA turn). Providers that don't support a
        per-call timeout (the cloud SDKs manage their own) ignore it.
        """
