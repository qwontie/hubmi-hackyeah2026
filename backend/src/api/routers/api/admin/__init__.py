from fastapi import APIRouter, Depends

from api.security import current_admin

from . import audit, clusters, imports, innovations, needs, stats

router = APIRouter(dependencies=[Depends(current_admin)])
router.include_router(needs.router, prefix="/needs", tags=["admin"])
router.include_router(innovations.router, prefix="/innovations", tags=["admin"])
router.include_router(imports.router, prefix="/import", tags=["admin"])
router.include_router(stats.router, prefix="/stats", tags=["admin"])
router.include_router(clusters.router, prefix="/clusters", tags=["admin"])
router.include_router(audit.router, prefix="/audit", tags=["admin"])
