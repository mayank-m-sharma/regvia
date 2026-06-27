"""Retrieval service — nearest-neighbour chunk lookup via pgvector."""

import uuid

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.embedding import Embedding
from app.services.embedding import get_embedding_provider

_SIMILARITY_THRESHOLD = 0.3


class RetrievedChunk(BaseModel):
    chunk_id: uuid.UUID
    text: str
    page_number: int | None
    similarity: float


class RetrievalService:
    """Embed a query and retrieve the most similar chunks from the database."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def retrieve(
        self,
        query: str,
        document_id: uuid.UUID,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        provider = get_embedding_provider()
        logger.info(
            "retrieval_start | provider={} document_id={}",
            type(provider).__name__,
            document_id,
        )
        vectors = await provider.embed([query])
        query_vec: list[float] = vectors[0]

        similarity_expr = (1 - Embedding.embedding.cosine_distance(query_vec)).label(
            "similarity"
        )

        stmt = (
            select(
                Chunk.id,
                Chunk.text,
                Chunk.page_number,
                similarity_expr,
            )
            .join(Chunk, Chunk.id == Embedding.chunk_id)
            .where(Chunk.document_id == document_id)
            .order_by(Embedding.embedding.cosine_distance(query_vec))
            .limit(top_k)
        )

        result = await self._session.execute(stmt)
        rows = result.fetchall()

        chunks: list[RetrievedChunk] = []
        for row in rows:
            similarity: float = float(row.similarity)
            if similarity < _SIMILARITY_THRESHOLD:
                continue
            chunks.append(
                RetrievedChunk(
                    chunk_id=row.id,
                    text=row.text,
                    page_number=row.page_number,
                    similarity=similarity,
                )
            )

        logger.info(
            "retrieval_complete | document_id={} returned={} (above threshold)",
            document_id,
            len(chunks),
        )
        return chunks
