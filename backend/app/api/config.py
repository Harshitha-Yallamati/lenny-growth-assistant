from fastapi import APIRouter

from app.api.schemas import ConfigResponse, ConfigUpdateRequest
from app.core.config import get_settings
from app.core.runtime_state import get_active_provider, set_active_provider
from app.llm.registry import provider_status

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    settings = get_settings()
    return ConfigResponse(
        active_provider=get_active_provider(),
        configured_default=settings.llm_provider,
        provider_status=await provider_status(),
        ollama_model=settings.ollama_model,
        anthropic_model=settings.anthropic_model,
        openai_model=settings.openai_model,
    )


@router.post("", response_model=ConfigResponse)
async def update_config(payload: ConfigUpdateRequest) -> ConfigResponse:
    set_active_provider(payload.provider)
    return await get_config()
