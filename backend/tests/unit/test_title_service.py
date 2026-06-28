"""Unit tests for title_service.generate_session_title."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.title_service import generate_session_title


@pytest.mark.asyncio
async def test_generate_title_returns_llm_output() -> None:
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Data Retention Requirements"

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch(
        "app.services.title_service._get_llm_client",
        return_value=(mock_client, "gpt-4o-mini"),
    ):
        title = await generate_session_title(
            "What are the retention requirements?", "You must retain data for 5 years."
        )

    assert title == "Data Retention Requirements"


@pytest.mark.asyncio
async def test_generate_title_strips_quotes() -> None:
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '"Data Retention Policy"'

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch(
        "app.services.title_service._get_llm_client",
        return_value=(mock_client, "gpt-4o-mini"),
    ):
        title = await generate_session_title("question", "answer")

    assert title == "Data Retention Policy"


@pytest.mark.asyncio
async def test_generate_title_falls_back_on_error() -> None:
    with patch(
        "app.services.title_service._get_llm_client",
        side_effect=RuntimeError("no provider"),
    ):
        title = await generate_session_title(
            "What are the data retention requirements?", "answer"
        )

    assert "data retention" in title.lower()


@pytest.mark.asyncio
async def test_generate_title_truncates_long_question() -> None:
    long_question = "x" * 100
    with patch(
        "app.services.title_service._get_llm_client",
        side_effect=RuntimeError("no provider"),
    ):
        title = await generate_session_title(long_question, "answer")

    assert len(title) <= 63  # 60 chars + ellipsis (3 chars)
    assert title.endswith("…")


@pytest.mark.asyncio
async def test_generate_title_falls_back_on_empty_response() -> None:
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = ""

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    question = "Short question"
    with patch(
        "app.services.title_service._get_llm_client",
        return_value=(mock_client, "gpt-4o-mini"),
    ):
        title = await generate_session_title(question, "answer")

    assert title == question
