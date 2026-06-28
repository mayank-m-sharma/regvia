"""Unit tests for chat session management endpoints (REGVIA-029)."""

import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.core.auth import get_current_user
from app.db.session import get_db
from app.main import app
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DOCUMENT_ID = uuid.uuid4()
_SESSION_ID = uuid.uuid4()
_USER_ID = uuid.uuid4()
_MESSAGE_ID = uuid.uuid4()


def _make_stub_user() -> MagicMock:
    user = MagicMock(spec=User)
    user.id = _USER_ID
    user.email = "test@example.com"
    user.display_name = "Test User"
    return user


def _make_ready_document() -> MagicMock:
    doc = MagicMock()
    doc.id = _DOCUMENT_ID
    doc.filename = "policy.pdf"
    doc.status = "ready"
    return doc


def _make_session(
    title: str | None = None,
    last_message_at: datetime | None = None,
) -> MagicMock:
    sess = MagicMock()
    sess.id = _SESSION_ID
    sess.document_id = _DOCUMENT_ID
    sess.user_id = _USER_ID
    sess.title = title
    sess.created_at = datetime.now(UTC)
    sess.last_message_at = last_message_at
    sess.messages = []
    sess.document = _make_ready_document()
    return sess


@pytest.fixture()
def override_auth_user() -> Generator[MagicMock, None, None]:
    stub = _make_stub_user()

    async def _mock() -> MagicMock:
        return stub

    app.dependency_overrides[get_current_user] = _mock
    yield stub
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# POST /api/v1/chat/sessions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_session_returns_201(
    async_client: AsyncClient,
    override_auth_user: MagicMock,
) -> None:
    doc = _make_ready_document()
    session = _make_session()

    async def _execute(stmt: object, params: object = None) -> MagicMock:  # noqa: ANN001
        result = MagicMock()
        result.scalar_one_or_none.return_value = doc
        return result

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=_execute)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    async def _refresh(obj: object) -> None:
        obj.id = session.id  # type: ignore[attr-defined]
        obj.created_at = session.created_at  # type: ignore[attr-defined]
        obj.last_message_at = None  # type: ignore[attr-defined]
        obj.title = None  # type: ignore[attr-defined]

    mock_db.refresh = AsyncMock(side_effect=_refresh)

    async def _mock_db() -> AsyncGenerator[MagicMock, None]:
        yield mock_db

    app.dependency_overrides[get_db] = _mock_db
    try:
        response = await async_client.post(
            "/api/v1/chat/sessions",
            json={"document_id": str(_DOCUMENT_ID)},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["document_id"] == str(_DOCUMENT_ID)
    assert data["message_count"] == 0


@pytest.mark.asyncio
async def test_create_session_404_on_unknown_document(
    async_client: AsyncClient,
    override_auth_user: MagicMock,
) -> None:
    async def _execute(stmt: object, params: object = None) -> MagicMock:  # noqa: ANN001
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        return result

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=_execute)

    async def _mock_db() -> AsyncGenerator[MagicMock, None]:
        yield mock_db

    app.dependency_overrides[get_db] = _mock_db
    try:
        response = await async_client.post(
            "/api/v1/chat/sessions",
            json={"document_id": str(uuid.uuid4())},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/chat/sessions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_sessions_returns_sorted_list(
    async_client: AsyncClient,
    override_auth_user: MagicMock,
) -> None:
    session = _make_session(title="GDPR Obligations")

    async def _execute(stmt: object, params: object = None) -> MagicMock:  # noqa: ANN001
        result = MagicMock()
        result.__iter__ = MagicMock(return_value=iter([(session, "policy.pdf", 3)]))
        return result

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=_execute)

    async def _mock_db() -> AsyncGenerator[MagicMock, None]:
        yield mock_db

    app.dependency_overrides[get_db] = _mock_db
    try:
        response = await async_client.get("/api/v1/chat/sessions")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    sessions = response.json()["data"]
    assert len(sessions) == 1
    assert sessions[0]["title"] == "GDPR Obligations"
    assert sessions[0]["message_count"] == 3
    assert sessions[0]["document_filename"] == "policy.pdf"


@pytest.mark.asyncio
async def test_list_sessions_returns_empty_when_none(
    async_client: AsyncClient,
    override_auth_user: MagicMock,
) -> None:
    async def _execute(stmt: object, params: object = None) -> MagicMock:  # noqa: ANN001
        result = MagicMock()
        result.__iter__ = MagicMock(return_value=iter([]))
        return result

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=_execute)

    async def _mock_db() -> AsyncGenerator[MagicMock, None]:
        yield mock_db

    app.dependency_overrides[get_db] = _mock_db
    try:
        response = await async_client.get("/api/v1/chat/sessions")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json()["data"] == []


# ---------------------------------------------------------------------------
# GET /api/v1/chat/sessions/{session_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_session_returns_messages(
    async_client: AsyncClient,
    override_auth_user: MagicMock,
) -> None:
    msg = MagicMock()
    msg.id = _MESSAGE_ID
    msg.role = MagicMock()
    msg.role.value = "user"
    msg.content = "What are the retention rules?"
    msg.citations = []
    msg.created_at = datetime.now(UTC)

    session = _make_session(title="Retention Rules")
    session.messages = [msg]

    async def _execute(stmt: object, params: object = None) -> MagicMock:  # noqa: ANN001
        result = MagicMock()
        result.scalar_one_or_none.return_value = session
        return result

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=_execute)

    async def _mock_db() -> AsyncGenerator[MagicMock, None]:
        yield mock_db

    app.dependency_overrides[get_db] = _mock_db
    try:
        response = await async_client.get(f"/api/v1/chat/sessions/{_SESSION_ID}")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == "Retention Rules"
    assert len(data["messages"]) == 1
    assert data["messages"][0]["content"] == "What are the retention rules?"


@pytest.mark.asyncio
async def test_get_session_404_on_wrong_user(
    async_client: AsyncClient,
    override_auth_user: MagicMock,
) -> None:
    async def _execute(stmt: object, params: object = None) -> MagicMock:  # noqa: ANN001
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        return result

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=_execute)

    async def _mock_db() -> AsyncGenerator[MagicMock, None]:
        yield mock_db

    app.dependency_overrides[get_db] = _mock_db
    try:
        response = await async_client.get(f"/api/v1/chat/sessions/{uuid.uuid4()}")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sessions_endpoints_require_auth(async_client: AsyncClient) -> None:
    r1 = await async_client.get("/api/v1/chat/sessions")
    r2 = await async_client.post(
        "/api/v1/chat/sessions", json={"document_id": str(_DOCUMENT_ID)}
    )
    assert r1.status_code == 401
    assert r2.status_code == 401
