"""In-memory runtime overrides for the LLM provider toggle.

Separate from Settings (which is env-driven and effectively immutable) so an
evaluator can flip providers from the UI without restarting the backend.
Intentionally not persisted anywhere — a restart resets to the .env default.
"""

from app.core.config import Provider, get_settings

_override: Provider | None = None


def get_active_provider() -> Provider:
    return _override or get_settings().llm_provider


def set_active_provider(provider: Provider) -> None:
    global _override
    _override = provider


def reset_override() -> None:
    global _override
    _override = None
