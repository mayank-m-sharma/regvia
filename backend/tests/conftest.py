"""Shared pytest fixtures for the RegVia backend test suite."""

import os
import uuid
from collections.abc import AsyncGenerator, Generator
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.auth import get_current_user
from app.main import app
from app.models.user import User
from tests.factories import (
    ChatSessionFactory,
    ChunkFactory,
    DocumentFactory,
    EmbeddingFactory,
    UserFactory,
)

# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------


def _test_db_url() -> str:
    """Resolve the test database URL from environment."""
    if url := os.getenv("TEST_DATABASE_URL"):
        return url
    base = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://regvia:regvia@localhost:5432/regvia"
    )
    # Append _test suffix to the DB name so we never touch the dev database.
    return base.rstrip("/") + "_test" if not base.endswith("_test") else base


@pytest.fixture(scope="session")
def test_db_url() -> str:
    return _test_db_url()


@pytest.fixture()
async def test_db(test_db_url: str) -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async SQLAlchemy session that rolls back after every test.

    The rollback ensures tests are fully isolated — no data leaks between them.
    DB models are not yet defined (REGVIA-004); this fixture is a placeholder
    that will be augmented with table creation once models exist.
    """
    engine = create_async_engine(test_db_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        # Savepoint so we can roll back without closing the connection.
        await conn.begin_nested()

    async with factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()


# ---------------------------------------------------------------------------
# HTTP client fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client wired directly to the FastAPI app (no network)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Factory fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def document_factory() -> type[DocumentFactory]:
    return DocumentFactory


@pytest.fixture()
def chunk_factory() -> type[ChunkFactory]:
    return ChunkFactory


@pytest.fixture()
def embedding_factory() -> type[EmbeddingFactory]:
    return EmbeddingFactory


@pytest.fixture()
def chat_session_factory() -> type[ChatSessionFactory]:
    return ChatSessionFactory


@pytest.fixture()
def user_factory() -> type[UserFactory]:
    return UserFactory


# ---------------------------------------------------------------------------
# Auth override fixture — injects a stub user so protected routes work in tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def stub_user() -> MagicMock:
    """Return a MagicMock User for dependency injection — no real DB needed."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.google_sub = "google-sub-test"
    user.email = "test@example.com"
    user.display_name = "Test User"
    user.avatar_url = None
    user.last_login_at = None
    return user


@pytest.fixture()
def override_auth(stub_user: MagicMock) -> Generator[MagicMock, None, None]:
    """Override get_current_user to return a stub user — no JWT required in tests."""

    async def _mock_auth() -> MagicMock:
        return stub_user

    app.dependency_overrides[get_current_user] = _mock_auth
    yield stub_user
    app.dependency_overrides.pop(get_current_user, None)
