import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import conflict, invalid, not_found
from api.security import AdminPerson
from services.dialogue.audit import record
from services.needs import merge_clusters, refresh_cluster_summary, split_cluster
from services.stats.clusters import (
    AdminCluster,
    ClusterPage,
    ClusterQuery,
    MergeBody,
    SplitBody,
    SplitResult,
    list_clusters,
    one,
)

router = APIRouter(route_class=DishkaRoute)

MISSING = "Nie znaleziono grupy zgłoszeń."
SELF_MERGE = "Nie można połączyć grupy z nią samą."
BAD_SPLIT = "Wybierz część zgłoszeń z tej grupy, ale nie wszystkie."


async def existing(session: AsyncSession, cluster_id: uuid.UUID) -> AdminCluster:
    cluster = await one(session, cluster_id)
    if cluster is None:
        raise not_found(MISSING)
    return cluster


@router.get("")
async def clusters(
    query: Annotated[ClusterQuery, Query()], session: FromDishka[AsyncSession]
) -> ClusterPage:
    items, total = await list_clusters(session, query)
    return ClusterPage(
        items=items, total=total, page=query.page, per_page=query.per_page
    )


@router.get("/{cluster_id}")
async def cluster(
    cluster_id: uuid.UUID, session: FromDishka[AsyncSession]
) -> AdminCluster:
    return await existing(session, cluster_id)


@router.post("/{cluster_id}/merge")
async def merge(
    cluster_id: uuid.UUID,
    body: MergeBody,
    admin: AdminPerson,
    session: FromDishka[AsyncSession],
) -> AdminCluster:
    if cluster_id == body.into_id:
        raise conflict(SELF_MERGE)
    await existing(session, cluster_id)
    await existing(session, body.into_id)
    record(
        session,
        admin,
        "cluster.merge",
        target=("need_cluster", cluster_id),
        details={"into_id": str(body.into_id)},
    )
    target = await merge_clusters(session, cluster_id, body.into_id)
    return await existing(session, target.id)


@router.post("/{cluster_id}/split")
async def split(
    cluster_id: uuid.UUID,
    body: SplitBody,
    admin: AdminPerson,
    session: FromDishka[AsyncSession],
) -> SplitResult:
    await existing(session, cluster_id)
    record(
        session,
        admin,
        "cluster.split",
        target=("need_cluster", cluster_id),
        details={"need_ids": [str(need_id) for need_id in body.need_ids]},
    )
    try:
        source, created = await split_cluster(session, cluster_id, body.need_ids)
    except ValueError as exc:
        await session.rollback()
        field = "need_ids"
        raise invalid(field, BAD_SPLIT) from exc
    return SplitResult(
        source=await existing(session, source.id),
        created=await existing(session, created.id),
    )


@router.post("/{cluster_id}/refresh")
async def refresh(
    cluster_id: uuid.UUID, admin: AdminPerson, session: FromDishka[AsyncSession]
) -> AdminCluster:
    await existing(session, cluster_id)
    record(session, admin, "cluster.refresh", target=("need_cluster", cluster_id))
    await session.commit()
    await refresh_cluster_summary(cluster_id)
    session.expire_all()
    return await existing(session, cluster_id)
