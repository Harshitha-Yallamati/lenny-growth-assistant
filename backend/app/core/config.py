from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["ollama", "anthropic", "openai"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"

    database_url: str = "postgresql+psycopg://lenny:lenny@localhost:5432/lenny_growth_assistant"

    llm_provider: Provider = "ollama"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    # Covers ordinary QA/artifact turns. Kept modest on purpose -- a genuinely
    # stuck Ollama shouldn't hang a simple question for as long as an essay
    # is allowed to run (see ollama_ship30_timeout_seconds below).
    ollama_timeout_seconds: float = 600.0
    # Ship 30 essays get their own, longer budget: measured at ~18 minutes
    # total for the two-pass draft+retry flow on CPU-only hardware with
    # llama3.1, i.e. up to ~9-10 min for a single pass before cold-load and
    # hardware variance -- 600s was observed to occasionally fall short of a
    # single pass. This is per-call, not per-essay, so it must comfortably
    # exceed one pass, not the whole two-pass total.
    ollama_ship30_timeout_seconds: float = 1200.0

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    retrieval_top_k: int = 5
    data_dir: str = "/app/data"
    # Minimum ts_rank for a chunk to count as relevant. Measured on this
    # corpus: on-topic questions score ~0.05-0.08, off-topic ones ~0.02.
    # Raise it to make "not grounded" stricter, lower it for more recall.
    retrieval_min_rank: float = 0.03

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
