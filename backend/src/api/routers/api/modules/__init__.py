from fastapi import APIRouter

from . import kreator, middleman, tester

router = APIRouter()
for module in (tester, middleman, kreator):
    router.include_router(module.public)
    router.include_router(module.admin, prefix="/admin")
