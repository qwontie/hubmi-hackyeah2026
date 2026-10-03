from fastapi import APIRouter, Depends

from api.security import current_admin

from . import needs

router = APIRouter(dependencies=[Depends(current_admin)])
router.include_router(needs.router, prefix="/needs", tags=["admin"])
