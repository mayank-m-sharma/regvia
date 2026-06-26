"""Local dev seed script — populates DB with a sample ready document.

Run: uv run python -m scripts.seed
Never runs in production.
"""

import asyncio
import random

from faker import Faker
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.settings import settings
from app.models import Base  # noqa: F401
from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus
from app.models.embedding import Embedding

fake = Faker()

NUM_CHUNKS = 5


async def seed() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        async with session.begin():
            doc = Document(
                filename="sample-gdpr-policy.pdf",
                s3_key="documents/seed/sample-gdpr-policy.pdf",
                size_bytes=204_800,
                status=DocumentStatus.ready,
                chunk_count=NUM_CHUNKS,
            )
            session.add(doc)
            await session.flush()

            for i in range(NUM_CHUNKS):
                chunk = Chunk(
                    document_id=doc.id,
                    chunk_index=i,
                    page_number=i + 1,
                    text=fake.paragraph(nb_sentences=8),
                    token_count=random.randint(200, 512),
                )
                session.add(chunk)
                await session.flush()

                emb = Embedding(
                    chunk_id=chunk.id,
                    embedding=[random.uniform(-1.0, 1.0) for _ in range(1536)],
                )
                session.add(emb)

        print(f"Seeded document: {doc.id} — {doc.filename}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
