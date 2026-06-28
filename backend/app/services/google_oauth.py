"""Google OAuth2 helpers — authorization URL, token exchange, user info."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.settings import settings

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


@dataclass
class GoogleUserInfo:
    sub: str
    email: str
    name: str | None
    picture: str | None


def generate_state() -> str:
    """Return a cryptographically random state token for CSRF protection."""
    return secrets.token_urlsafe(32)


def build_authorization_url(state: str) -> str:
    """Return the Google OAuth2 authorization URL."""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    return f"{_GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict[str, object]:
    """Exchange an authorization *code* for Google OAuth tokens."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            },
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]


async def get_google_user_info(access_token: str) -> GoogleUserInfo:
    """Fetch Google user info using the *access_token*."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        data: dict[str, object] = response.json()

    return GoogleUserInfo(
        sub=str(data["sub"]),
        email=str(data.get("email", "")),
        name=str(data["name"]) if data.get("name") else None,
        picture=str(data["picture"]) if data.get("picture") else None,
    )
