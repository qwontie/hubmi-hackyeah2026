from fastapi import APIRouter

from . import api
from .api import modules

router = APIRouter()
router.include_router(api.router, prefix="/api")
router.include_router(modules.router, prefix="/api")
