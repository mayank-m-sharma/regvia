"""Add user_id, title, last_message_at to chat_sessions.

Revision ID: e3f4a5b6c7d8
Revises: c1d2e3f4a5b6
Create Date: 2026-06-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e3f4a5b6c7d8"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,  # nullable so existing rows are valid
        ),
    )
    op.add_column(
        "chat_sessions",
        sa.Column("title", sa.Text(), nullable=True),
    )
    op.add_column(
        "chat_sessions",
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_chat_sessions_user_id", "chat_sessions", ["user_id"]
    )
    op.create_index(
        "ix_chat_sessions_last_message_at", "chat_sessions", ["last_message_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_chat_sessions_last_message_at", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_user_id", table_name="chat_sessions")
    op.drop_column("chat_sessions", "last_message_at")
    op.drop_column("chat_sessions", "title")
    op.drop_column("chat_sessions", "user_id")
