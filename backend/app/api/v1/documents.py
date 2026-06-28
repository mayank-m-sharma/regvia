import hashlib
import re
import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    UploadFile,
)
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.settings import settings
from app.db.session import get_db
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.document import DocumentResponse
from app.schemas.summary import SummaryResponse
from app.services.processing import process_document
from app.services.summary import SummaryService, get_document_or_raise_for_summary
from app.storage.client import storage_client

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(get_current_user)],
)

MAX_FILE_SIZE = 52_428_800  # 50 MB
FILENAME_RE = re.compile(r"^[\w\-]+\.pdf$")


def _sanitize_filename(filename: str) -> str:
    """Return a sanitized PDF filename."""
    name = filename.strip().lower()
    if not FILENAME_RE.match(name):
        stem = name.rsplit(".", 1)[0]
        name = re.sub(r"[^\w\-]", "_", stem) + ".pdf"
    return name


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# GET /documents  — list the current user's documents
# ---------------------------------------------------------------------------


@router.get("", response_model=ApiResponse[list[DocumentResponse]])
async def list_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    in_library: bool | None = Query(default=None),
) -> ApiResponse[list[DocumentResponse]]:
    """List documents owned by the current user, optionally filtered by in_library."""
    stmt = (
        select(Document)
        .where(Document.owner_id == current_user.id)
        .order_by(Document.created_at.desc())
    )
    if in_library is not None:
        stmt = stmt.where(Document.in_library.is_(in_library))

    result = await db.execute(stmt)
    docs = list(result.scalars().all())
    return ApiResponse(data=[DocumentResponse.model_validate(d) for d in docs])


# ---------------------------------------------------------------------------
# POST /documents  — upload a PDF and enqueue processing
# ---------------------------------------------------------------------------


@router.post("", status_code=202, response_model=ApiResponse[DocumentResponse])
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    in_library: bool = Query(default=False),
) -> ApiResponse[DocumentResponse]:
    """Upload a PDF document and enqueue background processing.

    Pass ``?in_library=true`` to add directly to the Knowledge Library.
    If the same content (by SHA-256) was already uploaded, the existing
    document is returned instead of re-uploading.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Only PDF files are supported.",
                "code": "INVALID_FILE_TYPE",
            },
        )

    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail={"message": "File exceeds 50MB limit.", "code": "FILE_TOO_LARGE"},
        )

    content_hash = _sha256(contents)
    sanitized = _sanitize_filename(file.filename or "document.pdf")

    # ── Duplicate detection ────────────────────────────────────────────────
    existing_result = await db.execute(
        select(Document).where(
            Document.owner_id == current_user.id,
            Document.content_hash == content_hash,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        # If caller wants it in library, promote it
        if in_library and not existing.in_library:
            existing.in_library = True
            await db.commit()
            await db.refresh(existing)
        logger.info(
            "document_duplicate | document_id={} in_library={}",
            existing.id,
            existing.in_library,
        )
        return ApiResponse(data=DocumentResponse.model_validate(existing))

    # ── New document ───────────────────────────────────────────────────────
    document_id = uuid.uuid4()
    s3_key = f"documents/{document_id}/{sanitized}"

    try:
        await storage_client.upload(s3_key, contents, "application/pdf")
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"message": "Failed to upload file.", "code": "UPLOAD_FAILED"},
        ) from exc

    doc = Document(
        id=document_id,
        filename=sanitized,
        s3_key=s3_key,
        size_bytes=len(contents),
        status=DocumentStatus.pending,
        owner_id=current_user.id,
        content_hash=content_hash,
        in_library=in_library,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    if settings.USE_CELERY:
        from app.worker.tasks import process_document_task

        process_document_task.delay(str(document_id))
        logger.info("document_enqueued_celery | document_id={}", document_id)
    else:
        background_tasks.add_task(process_document, str(document_id))
        logger.info("document_enqueued_background | document_id={}", document_id)

    return ApiResponse(data=DocumentResponse.model_validate(doc))


# ---------------------------------------------------------------------------
# GET /documents/{document_id}  — status poll
# ---------------------------------------------------------------------------


@router.get("/{document_id}", response_model=ApiResponse[DocumentResponse])
async def get_document(
    document_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[DocumentResponse]:
    """Retrieve document metadata and processing status."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail={"message": "Document not found.", "code": "DOCUMENT_NOT_FOUND"},
        )
    return ApiResponse(data=DocumentResponse.model_validate(doc))


# ---------------------------------------------------------------------------
# PATCH /documents/{document_id}/library  — add to knowledge library
# ---------------------------------------------------------------------------


@router.patch("/{document_id}/library", response_model=ApiResponse[DocumentResponse])
async def add_to_library(
    document_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[DocumentResponse]:
    """Mark a document as part of the current user's Knowledge Library."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail={"message": "Document not found.", "code": "DOCUMENT_NOT_FOUND"},
        )
    if not doc.in_library:
        doc.in_library = True
        await db.commit()
        await db.refresh(doc)
    return ApiResponse(data=DocumentResponse.model_validate(doc))


# ---------------------------------------------------------------------------
# POST /documents/{document_id}/summary  — compliance summary
# ---------------------------------------------------------------------------


@router.post(
    "/{document_id}/summary",
    status_code=202,
    response_model=ApiResponse[SummaryResponse],
)
async def get_or_generate_summary(
    document_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],  # noqa: B008
) -> ApiResponse[SummaryResponse]:
    """Generate (or return cached) compliance summary for a document."""
    await get_document_or_raise_for_summary(db, document_id)

    try:
        svc = SummaryService(db)
        summary = await svc.get_or_generate(document_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "summary_failed | document_id={}",
            document_id,
        )
        raise HTTPException(
            status_code=500,
            detail={"message": "Summary generation failed.", "code": "SUMMARY_FAILED"},
        ) from exc

    return ApiResponse(data=summary)
