import uuid
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.settings import settings
from app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.chunk import Chunk


class Embedding(UUIDMixin, Base):
    __tablename__ = "embeddings"

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.EMBEDDING_DIMENSIONS), nullable=False
    )

    chunk: Mapped["Chunk"] = relationship("Chunk", back_populates="embedding")
