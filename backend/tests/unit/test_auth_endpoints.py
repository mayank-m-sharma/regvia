"""Unit tests for /api/v1/auth endpoints."""

import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.auth import create_access_token, get_current_user
from app.db.session import get_db
from app.main import app
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stub_user(
    google_sub: str = "google-sub-123",
    email: str = "user@example.com",
) -> MagicMock:
    """Return a MagicMock that behaves like a User for endpoint tests."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.google_sub = google_sub
    user.email = email
    user.display_name = "Test User"
    user.avatar_url = None
    user.last_login_at = None
    user.created_at = datetime.now(UTC)
    return user


def _make_mock_db_with_user(user: User | None) -> MagicMock:
    """DB mock that returns *user* on first execute (user lookup)."""

    async def _execute(stmt: object, params: object = None) -> MagicMock:  # noqa: ANN001
        result = MagicMock()
        result.scalar_one_or_none.return_value = user
        return result

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=_execute)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    return mock_db


@pytest.fixture()
def override_db_no_user() -> Generator[None, None, None]:
    async def _mock() -> AsyncGenerator[MagicMock, None]:
        yield _make_mock_db_with_user(None)

    app.dependency_overrides[get_db] = _mock
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def override_db_existing_user() -> Generator[None, None, None]:
    user = _make_stub_user()

    async def _mock() -> AsyncGenerator[MagicMock, None]:
        yield _make_mock_db_with_user(user)

    app.dependency_overrides[get_db] = _mock
    yield
    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# GET /api/v1/auth/login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_returns_google_url(async_client: AsyncClient) -> None:
    with patch("app.services.google_oauth.settings") as mock_settings:
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_REDIRECT_URI = "http://localhost:5173/auth/callback"
        response = await async_client.get("/api/v1/auth/login")

    assert response.status_code == 200
    data = response.json()["data"]
    assert "url" in data
    assert "accounts.google.com" in data["url"]
    assert "test-client-id" in data["url"]


@pytest.mark.asyncio
async def test_login_returns_state(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/auth/login")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "state" in data
    assert len(data["state"]) > 0


@pytest.mark.asyncio
async def test_login_state_is_unique(async_client: AsyncClient) -> None:
    r1 = await async_client.get("/api/v1/auth/login")
    r2 = await async_client.get("/api/v1/auth/login")
    assert r1.json()["data"]["state"] != r2.json()["data"]["state"]


# ---------------------------------------------------------------------------
# POST /api/v1/auth/exchange
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exchange_creates_new_user_and_returns_token(
    async_client: AsyncClient,
    override_db_no_user: None,
) -> None:
    from app.services.google_oauth import GoogleUserInfo

    google_user = GoogleUserInfo(
        sub="google-sub-new",
        email="new@example.com",
        name="New User",
        picture=None,
    )

    with (
        patch(
            "app.api.v1.auth.exchange_code_for_tokens", new_callable=AsyncMock
        ) as mock_exchange,
        patch(
            "app.api.v1.auth.get_google_user_info", new_callable=AsyncMock
        ) as mock_info,
    ):
        mock_exchange.return_value = {"access_token": "goog-tok"}
        mock_info.return_value = google_user

        response = await async_client.post(
            "/api/v1/auth/exchange",
            json={"code": "auth-code"},
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert "token" in data
    assert len(data["token"]) > 0


@pytest.mark.asyncio
async def test_exchange_upserts_existing_user(
    async_client: AsyncClient,
    override_db_existing_user: None,
) -> None:
    from app.services.google_oauth import GoogleUserInfo

    google_user = GoogleUserInfo(
        sub="google-sub-123",
        email="user@example.com",
        name="Updated Name",
        picture=None,
    )

    with (
        patch(
            "app.api.v1.auth.exchange_code_for_tokens", new_callable=AsyncMock
        ) as mock_exchange,
        patch(
            "app.api.v1.auth.get_google_user_info", new_callable=AsyncMock
        ) as mock_info,
    ):
        mock_exchange.return_value = {"access_token": "goog-tok"}
        mock_info.return_value = google_user

        response = await async_client.post(
            "/api/v1/auth/exchange",
            json={"code": "auth-code"},
        )

    assert response.status_code == 200
    assert "token" in response.json()["data"]


@pytest.mark.asyncio
async def test_exchange_returns_502_when_google_fails(
    async_client: AsyncClient,
) -> None:
    with patch(
        "app.api.v1.auth.exchange_code_for_tokens", new_callable=AsyncMock
    ) as mock_exchange:
        mock_exchange.side_effect = RuntimeError("Google unreachable")

        response = await async_client.post(
            "/api/v1/auth/exchange",
            json={"code": "bad-code"},
        )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "OAUTH_FAILED"


@pytest.mark.asyncio
async def test_exchange_returns_502_when_no_access_token(
    async_client: AsyncClient,
) -> None:
    with patch(
        "app.api.v1.auth.exchange_code_for_tokens", new_callable=AsyncMock
    ) as mock_exchange:
        mock_exchange.return_value = {}  # no access_token key

        response = await async_client.post(
            "/api/v1/auth/exchange",
            json={"code": "code"},
        )

    assert response.status_code == 502


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_me_returns_user_when_authenticated(async_client: AsyncClient) -> None:
    stub = _make_stub_user()
    token = create_access_token(stub.id)

    async def _auth_override() -> User:
        return stub

    app.dependency_overrides[get_current_user] = _auth_override
    try:
        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == stub.email
    assert data["id"] == str(stub.id)


@pytest.mark.asyncio
async def test_me_returns_401_when_no_token(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_401_when_token_invalid(async_client: AsyncClient) -> None:
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer totally-invalid-token"},
    )
    assert response.status_code == 401
