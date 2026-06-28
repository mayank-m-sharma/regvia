import os
import sys

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.v1.router import router as v1_router
from app.core.settings import settings
from app.core.telemetry import configure_telemetry
from app.middleware.logging import RequestLoggingMiddleware

# ---------------------------------------------------------------------------
# Logging — JSON in production, human-readable in local dev
# ---------------------------------------------------------------------------

logger.remove()
# Ensure request_id is always present so the format string never raises KeyError
logger.configure(patcher=lambda record: record["extra"].setdefault("request_id", "-"))

if settings.LOG_FORMAT == "json":
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        serialize=True,  # emits newline-delimited JSON
        backtrace=False,
        diagnose=False,
    )
else:
    logger.add(
        sys.stdout,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level>"
            " | <cyan>{name}</cyan>:<cyan>{line}</cyan>"
            " | <dim>rid={extra[request_id]}</dim>"
            " - <level>{message}</level>"
        ),
        level=settings.LOG_LEVEL,
        backtrace=True,
        diagnose=True,
    )

# ---------------------------------------------------------------------------
# LangSmith — propagate settings into os.environ so the SDK picks them up
# (LangSmith reads os.environ directly, not our pydantic Settings object)
# ---------------------------------------------------------------------------

if settings.LANGCHAIN_TRACING_V2 and settings.LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
    logger.info("langsmith_enabled | project={}", settings.LANGCHAIN_PROJECT)

# ---------------------------------------------------------------------------
# OpenTelemetry (no-op when OTEL_ENABLED=false)
# ---------------------------------------------------------------------------

configure_telemetry()

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(title="RegVia API", version="0.1.0")

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://d2fb554do00st7.cloudfront.net"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        error = exc.detail
    else:
        error = {"message": str(exc.detail), "code": "ERROR"}
    return JSONResponse(
        status_code=exc.status_code,
        content={"data": None, "error": error},
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
