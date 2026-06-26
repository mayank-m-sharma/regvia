"""Smoke test — verifies the FastAPI app boots and /health responds."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(async_client: AsyncClient) -> None:
    response = await async_client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_returns_ok_status(async_client: AsyncClient) -> None:
    response = await async_client.get("/health")
    assert response.json() == {"status": "ok"}
