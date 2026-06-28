"""Unit tests for GET /api/v1/documents/{id}."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_unknown_document_returns_404(
    async_client: AsyncClient,
    override_auth: None,
) -> None:
    response = await async_client.get(f"/api/v1/documents/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"
