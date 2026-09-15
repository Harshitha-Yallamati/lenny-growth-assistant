import logging
from dataclasses import dataclass

from app.core.config import Provider, get_settings
from app.core.runtime_state import get_active_provider
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import LLMProvider
from app.llm.claude_agent_provider import ClaudeAgentSDKProvider, sdk_available
from app.llm.ollama_provider import OllamaProvider
from app.llm.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


@dataclass
class ResolvedProvider:
    provider: LLMProvider
    requested: Provider
    fell_back: bool


def _build_anthropic_provider() -> LLMProvider:
    """The Anthropic path prefers the Claude Agent SDK (the assignment's §3.1
    requirement) and falls back to the native Messages API when the SDK's
    runtime contract isn't met.

    The SDK drives the `claude` CLI as a subprocess, so it needs Node.js plus
    @anthropic-ai/claude-code present. That holds in our backend image, but not
    necessarily in a bare local venv -- and a missing CLI must degrade, never
    take the Anthropic path down entirely.
    """
    settings = get_settings()
    if sdk_available():
        return ClaudeAgentSDKProvider(settings.anthropic_api_key, settings.anthropic_model)

    logger.info(
        "claude_agent_sdk_unavailable_using_messages_api",
        extra={"event": "claude_agent_sdk_unavailable_using_messages_api", "provider": "anthropic"},
    )
    return AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model)


def _build_providers() -> dict[Provider, LLMProvider]:
    settings = get_settings()
    return {
        "ollama": OllamaProvider(
            settings.ollama_base_url, settings.ollama_model, settings.ollama_timeout_seconds
        ),
        "anthropic": _build_anthropic_provider(),
        "openai": OpenAIProvider(settings.openai_api_key, settings.openai_model),
    }


# Built once; provider objects are cheap and stateless aside from an HTTP/SDK client handle.
_providers = _build_providers()


async def resolve_provider() -> ResolvedProvider:
    """Pick the active provider, falling back to Ollama if it can't serve a request.

    This is the "flexible LLM configuration" fallback behavior required by the
    brief: if a cloud provider is selected but its key is missing/invalid or
    it's unreachable, we log a warning and transparently drop to the local
    model rather than failing the whole request.
    """
    requested = get_active_provider()
    provider = _providers[requested]

    if requested == "ollama":
        return ResolvedProvider(provider=provider, requested=requested, fell_back=False)

    if await provider.is_available():
        return ResolvedProvider(provider=provider, requested=requested, fell_back=False)

    logger.warning(
        "provider_fallback",
        extra={"event": "provider_fallback", "provider": requested},
    )
    return ResolvedProvider(provider=_providers["ollama"], requested=requested, fell_back=True)


async def provider_status() -> dict[str, bool]:
    status = {}
    for name, provider in _providers.items():
        status[name] = await provider.is_available()
    return status


def get_provider(name: Provider) -> LLMProvider:
    return _providers[name]
