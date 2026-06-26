import re
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.document import Document, DocumentStatus
from app.schemas.common import ApiResponse
from app.schemas.document import DocumentResponse
from app.services.processing import process_document
from app.storage.client import storage_client

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_FILE_SIZE = 52_428_800  # 50 MB
FILENAME_RE = re.compile(r"^[\w\-]+\.pdf$")


def _sanitize_filename(filename: str) -> str:
    """Return a sanitized PDF filename."""
    name = filename.strip().lower()
    if not FILENAME_RE.match(name):
        stem = name.rsplit(".", 1)[0]
        name = re.sub(r"[^\w\-]", "_", stem) + ".pdf"
    return name


@router.post("", status_code=202, response_model=ApiResponse[DocumentResponse])
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ApiResponse[DocumentResponse]:
    """Upload a PDF document and enqueue background processing."""
    # Validate MIME type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Only PDF files are supported.",
                "code": "INVALID_FILE_TYPE",
            },
        )

    # Read file into memory (needed for size check and upload)
    contents = await file.read()

    # Validate size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail={"message": "File exceeds 50MB limit.", "code": "FILE_TOO_LARGE"},
        )

    # Sanitize filename
    sanitized = _sanitize_filename(file.filename or "document.pdf")

    # Generate IDs
    document_id = uuid.uuid4()
    s3_key = f"documents/{document_id}/{sanitized}"

    # Upload to S3/MinIO
    try:
        await storage_client.upload(s3_key, contents, "application/pdf")
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"message": "Failed to upload file.", "code": "UPLOAD_FAILED"},
        ) from exc

    # Persist document record
    doc = Document(
        id=document_id,
        filename=sanitized,
        s3_key=s3_key,
        size_bytes=len(contents),
        status=DocumentStatus.pending,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Enqueue background processing
    background_tasks.add_task(process_document, str(document_id))

    return ApiResponse(data=DocumentResponse.model_validate(doc))


@router.get("/{document_id}", response_model=ApiResponse[DocumentResponse])
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ApiResponse[DocumentResponse]:
    """Retrieve document metadata and processing status."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail={"message": "Document not found.", "code": "DOCUMENT_NOT_FOUND"},
        )
    return ApiResponse(data=DocumentResponse.model_validate(doc))
