from fastapi import APIRouter, Depends, Request

from api.limits import rate_limit
from api.security import current_admin

from . import (
    audit,
    clusters,
    contacts,
    experts,
    grants,
    ideas,
    imports,
    innovations,
    needs,
    replies,
    stats,
)

write_limit = rate_limit("admin_write", per_minute=120)


async def limit_writes(request: Request) -> None:
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        await write_limit(request)


router = APIRouter(dependencies=[Depends(current_admin), Depends(limit_writes)])
router.include_router(needs.router, prefix="/needs", tags=["admin"])
router.include_router(replies.router, prefix="/needs", tags=["admin"])
router.include_router(innovations.router, prefix="/innovations", tags=["admin"])
router.include_router(imports.router, prefix="/import", tags=["admin"])
router.include_router(stats.router, prefix="/stats", tags=["admin"])
router.include_router(clusters.router, prefix="/clusters", tags=["admin"])
router.include_router(audit.router, prefix="/audit", tags=["admin"])
router.include_router(ideas.router, prefix="/ideas", tags=["admin"])
router.include_router(experts.router)
router.include_router(grants.router)
router.include_router(contacts.router, tags=["admin"])
