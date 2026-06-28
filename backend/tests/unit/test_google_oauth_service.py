"""Unit tests for Google OAuth2 service helpers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.google_oauth import (
    GoogleUserInfo,
    build_authorization_url,
    exchange_code_for_tokens,
    generate_state,
    get_google_user_info,
)


def test_generate_state_returns_string() -> None:
    state = generate_state()
    assert isinstance(state, str)
    assert len(state) > 20


def test_generate_state_is_unique() -> None:
    assert generate_state() != generate_state()


def test_build_authorization_url_contains_client_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.google_oauth.settings.GOOGLE_CLIENT_ID", "test-client-id"
    )
    url = build_authorization_url("some-state")
    assert "test-client-id" in url


def test_build_authorization_url_contains_state() -> None:
    url = build_authorization_url("my-test-state")
    assert "my-test-state" in url


def test_build_authorization_url_contains_required_scopes() -> None:
    url = build_authorization_url("state")
    assert "openid" in url
    assert "email" in url
    assert "profile" in url


def test_build_authorization_url_contains_redirect_uri(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.google_oauth.settings.GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/v1/auth/callback",
    )
    url = build_authorization_url("state")
    assert "localhost" in url


@pytest.mark.asyncio
async def test_exchange_code_calls_google_token_endpoint() -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "tok", "id_token": "id"}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.google_oauth.httpx.AsyncClient", return_value=mock_client):
        result = await exchange_code_for_tokens("auth-code")

    assert result["access_token"] == "tok"
    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert "oauth2.googleapis.com/token" in call_kwargs[0][0]


@pytest.mark.asyncio
async def test_get_google_user_info_returns_user_info() -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "sub": "12345",
        "email": "user@example.com",
        "name": "Test User",
        "picture": "https://example.com/photo.jpg",
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.google_oauth.httpx.AsyncClient", return_value=mock_client):
        info = await get_google_user_info("access-token")

    assert isinstance(info, GoogleUserInfo)
    assert info.sub == "12345"
    assert info.email == "user@example.com"
    assert info.name == "Test User"
    assert info.picture == "https://example.com/photo.jpg"


@pytest.mark.asyncio
async def test_get_google_user_info_handles_missing_optional_fields() -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {"sub": "999", "email": "anon@example.com"}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.google_oauth.httpx.AsyncClient", return_value=mock_client):
        info = await get_google_user_info("access-token")

    assert info.name is None
    assert info.picture is None
