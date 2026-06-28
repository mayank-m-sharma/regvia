from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.documents import router as documents_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(documents_router)
router.include_router(chat_router)
