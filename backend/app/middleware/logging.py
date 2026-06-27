"""Request logging middleware — injects request_id and logs each HTTP request."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Per-request structured log with request_id, method, path, status, duration."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = str(uuid.uuid4())
        start = time.monotonic()

        with logger.contextualize(request_id=request_id):
            response = await call_next(request)
            duration_ms = round((time.monotonic() - start) * 1000, 1)

            logger.info(
                "http_request | method={} path={} status={} duration_ms={}",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )

        response.headers["X-Request-Id"] = request_id
        return response
