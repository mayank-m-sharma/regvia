"""configurable_embedding_dimensions

Revision ID: a1b2c3d4e5f6
Revises: 2f36fa197b64
Create Date: 2026-06-26 20:23:47.730922

Drops and recreates the embeddings.embedding column using the dimension
configured via EMBEDDING_DIMENSIONS (default 1536).  Run after changing
EMBEDDING_DIMENSIONS in your .env.local — existing embedding rows are lost
because vector dimensions cannot be cast in-place.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op
from app.core.settings import settings

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "2f36fa197b64"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Recreate embedding column with the configured number of dimensions."""
    dims = settings.EMBEDDING_DIMENSIONS

    op.execute("DROP INDEX IF EXISTS embeddings_embedding_idx")
    op.drop_column("embeddings", "embedding")
    op.add_column(
        "embeddings",
        sa.Column("embedding", Vector(dims), nullable=False),
    )
    op.execute("CREATE INDEX ON embeddings USING hnsw (embedding vector_cosine_ops)")


def downgrade() -> None:
    """Restore embedding column to 1536 dimensions (OpenAI default)."""
    op.execute("DROP INDEX IF EXISTS embeddings_embedding_idx")
    op.drop_column("embeddings", "embedding")
    op.add_column(
        "embeddings",
        sa.Column("embedding", Vector(1536), nullable=False),
    )
    op.execute("CREATE INDEX ON embeddings USING hnsw (embedding vector_cosine_ops)")
