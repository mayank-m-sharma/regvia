"""Unit tests for ORM model definitions — no DB required."""

import uuid

from app.models import Base
from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus
from app.models.message import Message, MessageRole  # noqa: F401


def test_document_status_enum_values() -> None:
    assert set(DocumentStatus) == {
        DocumentStatus.pending,
        DocumentStatus.processing,
        DocumentStatus.ready,
        DocumentStatus.failed,
    }


def test_message_role_enum_values() -> None:
    assert set(MessageRole) == {MessageRole.user, MessageRole.assistant}


def test_document_default_status() -> None:
    doc = Document(
        filename="test.pdf",
        s3_key="documents/test/test.pdf",
        size_bytes=1024,
    )
    assert doc.status == DocumentStatus.pending


def test_all_models_registered_in_base_metadata() -> None:
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "documents",
        "chunks",
        "embeddings",
        "chat_sessions",
        "messages",
        "summaries",
        "users",
    }
    assert expected == table_names


def test_chunk_has_document_id_field() -> None:
    doc_id = uuid.uuid4()
    chunk = Chunk(
        document_id=doc_id,
        chunk_index=0,
        page_number=1,
        text="sample text",
        token_count=10,
    )
    assert chunk.document_id == doc_id
