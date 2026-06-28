"""Authentication endpoints — Google OAuth2 flow + JWT issuance."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ExchangeRequest,
    ExchangeResponse,
    LoginUrlResponse,
    UserResponse,
)
from app.schemas.common import ApiResponse
from app.services.google_oauth import (
    build_authorization_url,
    exchange_code_for_tokens,
    generate_state,
    get_google_user_info,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login", response_model=ApiResponse[LoginUrlResponse])
async def login() -> ApiResponse[LoginUrlResponse]:
    """Return the Google OAuth2 authorization URL and state token.

    The frontend stores the state in sessionStorage and validates it against
    the ``state`` query parameter returned by Google on callback.
    """
    state = generate_state()
    url = build_authorization_url(state)
    return ApiResponse(data=LoginUrlResponse(url=url, state=state))


@router.post("/exchange", response_model=ApiResponse[ExchangeResponse])
async def exchange(
    body: ExchangeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[ExchangeResponse]:
    """Exchange a Google authorization code for a RegVia JWT.

    The frontend calls this after validating that the ``state`` returned by
    Google matches the value it stored before the redirect.
    """
    # Exchange code for Google tokens
    try:
        token_data = await exchange_code_for_tokens(body.code)
    except Exception as exc:
        logger.exception("google_token_exchange_failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Failed to exchange code with Google.",
                "code": "OAUTH_FAILED",
            },
        ) from exc

    access_token = str(token_data.get("access_token", ""))
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Google did not return an access token.",
                "code": "OAUTH_FAILED",
            },
        )

    # Fetch user info from Google
    try:
        google_user = await get_google_user_info(access_token)
    except Exception as exc:
        logger.exception("google_userinfo_failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Failed to fetch user info from Google.",
                "code": "OAUTH_FAILED",
            },
        ) from exc

    # Upsert user row
    result = await db.execute(select(User).where(User.google_sub == google_user.sub))
    user = result.scalar_one_or_none()

    now = datetime.now(UTC)
    if user is None:
        user = User(
            google_sub=google_user.sub,
            email=google_user.email,
            display_name=google_user.name,
            avatar_url=google_user.picture,
            last_login_at=now,
        )
        db.add(user)
        logger.info("user_created | email={}", google_user.email)
    else:
        user.last_login_at = now
        if google_user.name:
            user.display_name = google_user.name
        if google_user.picture:
            user.avatar_url = google_user.picture
        logger.info("user_login | email={}", google_user.email)

    await db.commit()
    await db.refresh(user)

    jwt_token = create_access_token(user.id)
    return ApiResponse(data=ExchangeResponse(token=jwt_token))


@router.get("/me", response_model=ApiResponse[UserResponse])
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[UserResponse]:
    """Return the authenticated user's profile."""
    return ApiResponse(data=UserResponse.model_validate(current_user))
