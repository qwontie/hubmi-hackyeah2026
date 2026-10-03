from fastapi import APIRouter

from . import tester

router = APIRouter()
router.include_router(tester.public)
router.include_router(tester.admin, prefix="/admin")
