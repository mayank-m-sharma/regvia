from fastapi import APIRouter

from app.api.v1.documents import router as documents_router

router = APIRouter()
router.include_router(documents_router)
