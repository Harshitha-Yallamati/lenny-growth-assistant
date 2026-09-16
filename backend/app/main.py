import asyncio
import logging
import sys
from contextlib import asynccontextmanager

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import chat, config, health, sessions, sources
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.rag.ingest import ingest_transcripts, needs_ingestion

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        try:
            if await needs_ingestion(db):
                count = await ingest_transcripts(db)
                logger.info("startup_ingestion", extra={"event": "startup_ingestion", "provider": str(count)})
        except Exception:
            logger.exception("startup_ingestion_failed", extra={"event": "startup_ingestion_failed"})

    yield


app = FastAPI(title="The Lenny Growth Assistant", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.__class__.__name__, "detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Keep 422s on the same {error, detail} contract as every other error.

    FastAPI's default validation response is {"detail": [ {...}, ... ]} -- no
    `error` key, and `detail` is a list of objects rather than a string. The
    frontend does `body.detail ?? statusText` and renders the result straight
    into its error banner, so a validation failure surfaced as a stringified
    object instead of a readable message. Flatten it to "field: message" so
    the contract documented in architecture.md actually holds for every
    status code.
    """
    parts = []
    for err in exc.errors():
        location = ".".join(str(p) for p in err.get("loc", []) if p != "body") or "request"
        parts.append(f"{location}: {err.get('msg', 'invalid value')}")
    return JSONResponse(
        status_code=422,
        content={"error": "ValidationError", "detail": "; ".join(parts) or "Invalid request."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", extra={"event": "unhandled_exception"})
    return JSONResponse(
        status_code=500,
        content={"error": "InternalServerError", "detail": "An unexpected error occurred."},
    )


app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(config.router)
app.include_router(sources.router)
