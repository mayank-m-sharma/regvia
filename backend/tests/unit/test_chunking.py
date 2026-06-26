"""Unit tests for text chunking logic."""

import pytest
import tiktoken

from app.services.processing import CHUNK_SIZE, MIN_CHUNK_SIZE, _chunk_text


@pytest.fixture
def enc() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def test_chunk_size_respects_limit(enc: tiktoken.Encoding) -> None:
    # Generate text that encodes to ~600 tokens
    text = " ".join(["word"] * 600)
    chunks = _chunk_text(text, 1, enc)
    for chunk in chunks:
        assert chunk["token_count"] <= CHUNK_SIZE


def test_min_chunk_size_filter(enc: tiktoken.Encoding) -> None:
    # Short text under min chunk size should produce no chunks
    text = "Too short."
    chunks = _chunk_text(text, 1, enc)
    assert all(c["token_count"] >= MIN_CHUNK_SIZE for c in chunks)


def test_page_number_preserved(enc: tiktoken.Encoding) -> None:
    text = " ".join(["word"] * 200)
    chunks = _chunk_text(text, 7, enc)
    assert all(c["page_number"] == 7 for c in chunks)


def test_empty_text_produces_no_chunks(enc: tiktoken.Encoding) -> None:
    chunks = _chunk_text("", 1, enc)
    assert chunks == []
