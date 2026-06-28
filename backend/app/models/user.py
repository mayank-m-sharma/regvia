import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    google_sub: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # chat_sessions relationship added in REGVIA-029 when ChatSession.user_id FK exists

    __table_args__ = (
        Index("ix_users_google_sub", "google_sub", unique=True),
        Index("ix_users_email", "email", unique=True),
    )


# Keep a convenience alias for FK references
UserID = uuid.UUID
