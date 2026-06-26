"""Background document processing pipeline.

Steps:
1. Extract text from PDF (pdfplumber)
2. Chunk text (512 tokens, 50 token overlap, min 100 tokens)
3. Generate embeddings (text-embedding-3-small via OpenAI)
4. Update document status to ready
"""

import asyncio
import io
import logging
from typing import TypedDict
from uuid import UUID

import pdfplumber
import tiktoken
from openai import AsyncOpenAI
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus
from app.models.embedding import Embedding

logger = logging.getLogger(__name__)

CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
MIN_CHUNK_SIZE = 100
EMBEDDING_BATCH_SIZE = 100
EMBEDDING_MODEL = "text-embedding-3-small"


class ChunkData(TypedDict):
    text: str
    token_count: int
    page_number: int


def _chunk_text(
    text: str,
    page_number: int,
    enc: tiktoken.Encoding,
) -> list[ChunkData]:
    """Chunk a page's text into overlapping token windows."""
    tokens = enc.encode(text)
    chunks: list[ChunkData] = []
    start = 0
    while start < len(tokens):
        end = min(start + CHUNK_SIZE, len(tokens))
        chunk_tokens = tokens[start:end]
        if len(chunk_tokens) >= MIN_CHUNK_SIZE:
            chunks.append(
                ChunkData(
                    text=enc.decode(chunk_tokens),
                    token_count=len(chunk_tokens),
                    page_number=page_number,
                )
            )
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


async def _embed_batch(client: AsyncOpenAI, texts: list[str]) -> list[list[float]]:
    response = await client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


async def process_document(document_id: str) -> None:
    """Full processing pipeline. Sets status=failed on any error."""
    doc_uuid = UUID(document_id)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Document).where(Document.id == doc_uuid))
        doc = result.scalar_one_or_none()
        if doc is None or doc.status == DocumentStatus.ready:
            return  # idempotent

        doc.status = DocumentStatus.processing
        await session.commit()

        try:
            from app.storage.client import storage_client

            pdf_bytes: bytes = await asyncio.to_thread(
                lambda: storage_client._client.get_object(
                    Bucket=storage_client._bucket, Key=doc.s3_key
                )["Body"].read()
            )
            pdf_file = io.BytesIO(pdf_bytes)

            pages: list[tuple[int, str]] = []
            with pdfplumber.open(pdf_file) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    if len(text) >= 20:
                        pages.append((i, text))

            enc = tiktoken.get_encoding("cl100k_base")
            all_chunks: list[ChunkData] = []
            for page_num, text in pages:
                all_chunks.extend(_chunk_text(text, page_num, enc))

            openai_client = AsyncOpenAI()
            all_embeddings: list[list[float]] = []
            for i in range(0, len(all_chunks), EMBEDDING_BATCH_SIZE):
                batch = [c["text"] for c in all_chunks[i : i + EMBEDDING_BATCH_SIZE]]
                vecs = await _embed_batch(openai_client, batch)
                all_embeddings.extend(vecs)

            for idx, (chunk_data, vector) in enumerate(
                zip(all_chunks, all_embeddings, strict=True)
            ):
                chunk = Chunk(
                    document_id=doc_uuid,
                    chunk_index=idx,
                    page_number=chunk_data["page_number"],
                    text=chunk_data["text"],
                    token_count=chunk_data["token_count"],
                )
                session.add(chunk)
                await session.flush()

                emb = Embedding(chunk_id=chunk.id, embedding=vector)
                session.add(emb)

            doc.chunk_count = len(all_chunks)
            doc.status = DocumentStatus.ready
            await session.commit()

            logger.info(
                "document_processed",
                extra={"document_id": document_id, "chunk_count": len(all_chunks)},
            )

        except Exception:
            logger.exception(
                "document_processing_failed",
                extra={"document_id": document_id},
            )
            await session.rollback()
            doc.status = DocumentStatus.failed
            await session.commit()
