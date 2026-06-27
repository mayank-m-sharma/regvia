import sys

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.v1.router import router as v1_router
from app.core.settings import settings

# Remove default loguru handler and configure structured output
logger.remove()
logger.add(
    sys.stdout,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level>"
        " | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    ),
    level=settings.LOG_LEVEL,
    backtrace=True,
    diagnose=True,
)

app = FastAPI(title="RegVia API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
