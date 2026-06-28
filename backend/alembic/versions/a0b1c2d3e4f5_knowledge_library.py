"""REGVIA-030: Knowledge library — owner_id/content_hash/in_library on documents,
nullable document_id on chat_sessions.

Revision ID: a0b1c2d3e4f5
Revises: e3f4a5b6c7d8
Create Date: 2026-06-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a0b1c2d3e4f5"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── documents table ────────────────────────────────────────────────────────
    op.add_column(
        "documents",
        sa.Column(
            "owner_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column("content_hash", sa.Text(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "in_library",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])
    # Unique per-owner hash — only enforced when hash is not null
    op.execute(
        "CREATE UNIQUE INDEX uq_documents_owner_content_hash "
        "ON documents (owner_id, content_hash) "
        "WHERE content_hash IS NOT NULL"
    )

    # ── chat_sessions table ────────────────────────────────────────────────────
    # Make document_id nullable so library sessions can exist without a document
    op.alter_column("chat_sessions", "document_id", nullable=True)


def downgrade() -> None:
    # Restore chat_sessions.document_id NOT NULL (remove any null rows first)
    op.execute(
        "DELETE FROM chat_sessions WHERE document_id IS NULL"
    )
    op.alter_column("chat_sessions", "document_id", nullable=False)

    # Remove documents additions
    op.execute("DROP INDEX IF EXISTS uq_documents_owner_content_hash")
    op.drop_index("ix_documents_owner_id", table_name="documents")
    op.drop_column("documents", "in_library")
    op.drop_column("documents", "content_hash")
    op.drop_column("documents", "owner_id")
