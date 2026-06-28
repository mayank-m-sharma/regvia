import random
import uuid

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_session import ChatSession
from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus
from app.models.embedding import Embedding
from app.models.user import User

fake = Faker()


class UserFactory:
    @staticmethod
    async def create(session: AsyncSession, **kwargs: object) -> User:
        user = User(
            google_sub=str(kwargs.get("google_sub", fake.uuid4())),
            email=str(kwargs.get("email", fake.email())),
            display_name=str(kwargs.get("display_name", fake.name())),
            avatar_url=kwargs.get("avatar_url"),
        )
        session.add(user)
        await session.flush()
        return user


class DocumentFactory:
    @staticmethod
    async def create(session: AsyncSession, **kwargs: object) -> Document:
        doc = Document(
            filename=kwargs.get("filename", fake.file_name(extension="pdf")),
            s3_key=kwargs.get("s3_key", f"documents/{uuid.uuid4()}/test.pdf"),
            size_bytes=kwargs.get("size_bytes", random.randint(10_000, 5_000_000)),
            status=kwargs.get("status", DocumentStatus.ready),
            chunk_count=kwargs.get("chunk_count", None),
        )
        session.add(doc)
        await session.flush()
        return doc


class ChunkFactory:
    @staticmethod
    async def create(
        session: AsyncSession, document: Document, **kwargs: object
    ) -> Chunk:
        chunk = Chunk(
            document_id=document.id,
            chunk_index=kwargs.get("chunk_index", 0),
            page_number=kwargs.get("page_number", 1),
            text=kwargs.get("text", fake.paragraph(nb_sentences=5)),
            token_count=kwargs.get("token_count", random.randint(100, 512)),
        )
        session.add(chunk)
        await session.flush()
        return chunk


class EmbeddingFactory:
    @staticmethod
    async def create(
        session: AsyncSession, chunk: Chunk, **kwargs: object
    ) -> Embedding:
        vector = kwargs.get(
            "embedding", [random.uniform(-1.0, 1.0) for _ in range(1536)]
        )
        emb = Embedding(chunk_id=chunk.id, embedding=vector)
        session.add(emb)
        await session.flush()
        return emb


class ChatSessionFactory:
    @staticmethod
    async def create(
        session: AsyncSession, document: Document, **kwargs: object
    ) -> ChatSession:
        sess = ChatSession(document_id=document.id)
        session.add(sess)
        await session.flush()
        return sess
