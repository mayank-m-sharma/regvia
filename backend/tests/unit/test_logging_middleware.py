"""Unit tests for RequestLoggingMiddleware."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from app.middleware.logging import RequestLoggingMiddleware


def _make_app(status_code: int = 200) -> Starlette:
    async def homepage(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok", status_code=status_code)

    app = Starlette(routes=[Route("/", homepage), Route("/health", homepage)])
    app.add_middleware(RequestLoggingMiddleware)
    return app


@pytest.mark.asyncio
async def test_x_request_id_header_present() -> None:
    """Every response must include X-Request-Id."""
    transport = ASGITransport(app=_make_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert "x-request-id" in response.headers


@pytest.mark.asyncio
async def test_x_request_id_is_valid_uuid() -> None:
    """X-Request-Id must be a valid UUID string."""
    import uuid

    transport = ASGITransport(app=_make_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    request_id = response.headers["x-request-id"]
    uuid.UUID(request_id)  # raises if invalid


@pytest.mark.asyncio
async def test_different_requests_get_different_ids() -> None:
    """Each request must receive a unique request_id."""
    transport = ASGITransport(app=_make_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.get("/")
        r2 = await client.get("/")

    assert r1.headers["x-request-id"] != r2.headers["x-request-id"]


@pytest.mark.asyncio
async def test_middleware_logs_request() -> None:
    """Middleware emits an http_request log line via loguru for each request."""
    from loguru import logger

    captured: list[str] = []
    handler_id = logger.add(lambda msg: captured.append(msg), level="INFO")

    try:
        transport = ASGITransport(app=_make_app())
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/health")
    finally:
        logger.remove(handler_id)

    assert any("http_request" in line for line in captured)


@pytest.mark.asyncio
async def test_middleware_does_not_swallow_errors() -> None:
    """4xx responses still go through the middleware and get an X-Request-Id."""

    async def not_found(request: Request) -> PlainTextResponse:
        return PlainTextResponse("nope", status_code=404)

    app = Starlette(routes=[Route("/missing", not_found)])
    app.add_middleware(RequestLoggingMiddleware)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/missing")

    assert response.status_code == 404
    assert "x-request-id" in response.headers
