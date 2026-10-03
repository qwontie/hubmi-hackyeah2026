from fastapi import APIRouter

from . import admin, auth, dialogue, health, public, stream

router = APIRouter()
router.include_router(health.router, prefix="/health")
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(stream.router, prefix="/stream", tags=["stream"])
router.include_router(admin.router, prefix="/admin")
router.include_router(dialogue.router, prefix="/needs")
router.include_router(public.router)
