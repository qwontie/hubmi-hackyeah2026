from fastapi import APIRouter

from . import innovations, match, needs

router = APIRouter(tags=["public"])
router.include_router(match.router, prefix="/match")
router.include_router(needs.router, prefix="/needs")
router.include_router(innovations.router)
