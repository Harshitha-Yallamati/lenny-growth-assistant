import asyncio
import os
import sys
from pathlib import Path

# psycopg3's async mode can't run on Windows' default ProactorEventLoop, so the
# suite has to opt into the selector loop before pytest-asyncio builds one.
# Linux/macOS (and the Docker image) are unaffected.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Must run before any `app.*` import touches Settings (lru_cached at first call).
REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://lenny:lenny@localhost:5432/lenny_growth_assistant_test",
)
os.environ.setdefault("DATA_DIR", str(REPO_ROOT / "data"))
os.environ.setdefault("LLM_PROVIDER", "ollama")
os.environ.setdefault("ANTHROPIC_API_KEY", "")
os.environ.setdefault("OPENAI_API_KEY", "")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.core import runtime_state  # noqa: E402

TEST_DATABASE_URL = os.environ["DATABASE_URL"]


@pytest.fixture(autouse=True)
def _reset_provider_override():
    runtime_state.reset_override()
    yield
    runtime_state.reset_override()


@pytest_asyncio.fixture(scope="session")
async def _database():
    """Only requested by fixtures that actually need Postgres (`client`,
    `db_session`), so pure unit tests (routing, sanitization) can run without
    a database at all."""
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except OperationalError as exc:  # pragma: no cover
        # Only a genuine connection failure is a legitimate skip. Anything
        # else (a missing driver dependency, a schema error) is a real
        # failure and must not masquerade as "Postgres isn't running", or
        # it sends whoever runs the suite off debugging the wrong thing.
        pytest.skip(
            f"Postgres test database not reachable at {TEST_DATABASE_URL} ({exc}). "
            "Run `docker compose up -d db` first."
        )
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(_database):
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session(_database):
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session
