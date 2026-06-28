"""JWT creation, verification, and the FastAPI get_current_user dependency."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.db.session import get_db
from app.models.user import User

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def create_access_token(user_id: uuid.UUID) -> str:
    """Return a signed JWT for *user_id*."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(  # type: ignore[no-any-return]
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> uuid.UUID:
    """Verify *token* signature + expiry and return the user UUID.

    Raises ``HTTPException(401)`` on any failure.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"message": "Invalid or expired token.", "code": "UNAUTHORIZED"},
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        sub: str | None = payload.get("sub")
        if sub is None:
            raise credentials_exc
        return uuid.UUID(sub)
    except (JWTError, ValueError) as exc:
        raise credentials_exc from exc


async def get_current_user(
    token: Annotated[str | None, Depends(_oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """FastAPI dependency — resolve a valid JWT to the owning User row."""
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Authentication required.", "code": "UNAUTHORIZED"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = decode_access_token(token)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "User not found.", "code": "UNAUTHORIZED"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
