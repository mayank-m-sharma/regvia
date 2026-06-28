"""Retrieval service — nearest-neighbour chunk lookup via pgvector."""

import uuid
from collections.abc import Sequence
from typing import Any

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import Row, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus
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

    async def _embed_query(self, query: str) -> list[float]:
        provider = get_embedding_provider()
        vectors = await provider.embed([query])
        return vectors[0]

    async def retrieve(
        self,
        query: str,
        document_id: uuid.UUID,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Search within a single document."""
        logger.info(
            "retrieval_start | mode=single_doc document_id={}",
            document_id,
        )
        query_vec = await self._embed_query(query)

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
        return self._filter_and_build(rows, document_id=str(document_id))

    async def retrieve_from_library(
        self,
        query: str,
        owner_id: uuid.UUID,
        top_k: int = 10,
    ) -> list[RetrievedChunk]:
        """Search across all of a user's ready Knowledge Library documents."""
        logger.info(
            "retrieval_start | mode=library owner_id={}",
            owner_id,
        )
        query_vec = await self._embed_query(query)

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
            .join(Document, Chunk.document_id == Document.id)
            .where(
                Document.owner_id == owner_id,
                Document.status == DocumentStatus.ready,
                Document.in_library.is_(True),
            )
            .order_by(Embedding.embedding.cosine_distance(query_vec))
            .limit(top_k)
        )

        result = await self._session.execute(stmt)
        rows = result.fetchall()
        return self._filter_and_build(rows, document_id=f"library/{owner_id}")

    def _filter_and_build(
        self,
        rows: Sequence[Row[Any]],
        *,
        document_id: str,
    ) -> list[RetrievedChunk]:
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
