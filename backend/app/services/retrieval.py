"""Retrieval service — nearest-neighbour chunk lookup via pgvector."""

import uuid

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedding import get_embedding_provider

_NOT_FOUND_SENTINEL = "I could not find this information in the document."
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

        sql = text(
            """
            SELECT c.id, c.text, c.page_number, c.chunk_index,
                   1 - (e.embedding <=> :query_vec) AS similarity
            FROM embeddings e
            JOIN chunks c ON c.id = e.chunk_id
            WHERE c.document_id = :document_id
            ORDER BY e.embedding <=> :query_vec
            LIMIT :top_k
            """
        )

        result = await self._session.execute(
            sql,
            {
                "query_vec": str(query_vec),
                "document_id": str(document_id),
                "top_k": top_k,
            },
        )
        rows = result.fetchall()

        chunks: list[RetrievedChunk] = []
        for row in rows:
            similarity: float = float(row.similarity)
            if similarity < _SIMILARITY_THRESHOLD:
                continue
            chunks.append(
                RetrievedChunk(
                    chunk_id=uuid.UUID(str(row.id)),
                    text=str(row.text),
                    page_number=(
                        int(row.page_number) if row.page_number is not None else None
                    ),
                    similarity=similarity,
                )
            )

        logger.info(
            "retrieval_complete | document_id={} returned={} (above threshold)",
            document_id,
            len(chunks),
        )
        return chunks
