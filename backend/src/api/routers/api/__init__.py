from fastapi import APIRouter

from . import admin, auth, dialogue, expert, health, knowledge, public, stream

router = APIRouter()
router.include_router(health.router, prefix="/health")
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(stream.router, prefix="/stream", tags=["stream"])
router.include_router(admin.router, prefix="/admin")
router.include_router(expert.router, prefix="/expert")
router.include_router(knowledge.admin_router, prefix="/admin")
router.include_router(dialogue.router, prefix="/needs")
router.include_router(dialogue.ideas, prefix="/ideas")
router.include_router(public.router)
router.include_router(knowledge.router)
