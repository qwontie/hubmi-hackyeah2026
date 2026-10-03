from fastapi import APIRouter

from . import middleman, tester

router = APIRouter()
router.include_router(tester.public)
router.include_router(tester.admin, prefix="/admin")
router.include_router(middleman.public)
router.include_router(middleman.admin, prefix="/admin")
