from fastapi import APIRouter

from . import auth, health, stream

router = APIRouter()
router.include_router(health.router, prefix="/health")
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(stream.router, prefix="/stream", tags=["stream"])
