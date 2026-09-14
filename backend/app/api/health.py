import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.runtime_state import get_active_provider
from app.db.session import get_db
from app.llm.registry import provider_status

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    components = {}

    try:
        await db.execute(text("SELECT 1"))
        components["database"] = "ok"
    except SQLAlchemyError as exc:
        components["database"] = f"error: {exc}"

    providers = await provider_status()
    components["providers"] = providers
    components["active_provider"] = get_active_provider()

    overall_ok = components["database"] == "ok" and any(providers.values())
    return {"status": "ok" if overall_ok else "degraded", "components": components}
