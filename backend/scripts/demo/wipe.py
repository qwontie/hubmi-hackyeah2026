import asyncio
import sys
import uuid
from pathlib import Path

from rich.console import Console
from sqlalchemy import delete, func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dependencies.container import container
from scripts.demo import registry
from services.ai import AiUnavailableError
from services.needs import refresh_cluster_summary
from services.needs.clusters import recompute
from utils.db import init_db, session_scope
from utils.db.models import (
    AdminAction,
    AdminUser,
    DemoRecord,
    Feedback,
    Idea,
    Message,
    Need,
    NeedCluster,
    TestSignup,
)
from utils.db.models.adaptation import Adaptation
from utils.logging import setup_logging

console = Console()

type DemoModel = type[
    Feedback | TestSignup | Adaptation | Message | Need | Idea | AdminUser
]


async def remove(session: AsyncSession, model: DemoModel, ids: list[uuid.UUID]) -> int:
    if not ids:
        return 0
    result = await session.exec(delete(model).where(col(model.id).in_(ids)))
    return result.rowcount or 0


async def touched_clusters(
    session: AsyncSession, need_ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    rows = await session.exec(
        select(Need.cluster_id)
        .where(col(Need.id).in_(need_ids), col(Need.cluster_id).is_not(None))
        .distinct()
    )
    return {cluster_id for cluster_id in rows.all() if cluster_id is not None}


async def settle_clusters(
    session: AsyncSession, cluster_ids: set[uuid.UUID], demo: set[uuid.UUID]
) -> tuple[int, list[uuid.UUID]]:
    deleted = 0
    kept: list[uuid.UUID] = []
    for cluster_id in cluster_ids:
        cluster = await session.get(NeedCluster, cluster_id)
        if cluster is None:
            continue
        members = await session.scalar(
            select(func.count())
            .select_from(Need)
            .where(col(Need.cluster_id) == cluster_id)
        )
        if not members and cluster_id in demo:
            await session.delete(cluster)
            deleted += 1
        else:
            await recompute(session, cluster)
            kept.append(cluster_id)
    return deleted, kept


async def wipe(session: AsyncSession) -> dict[str, int]:
    ids = {kind: await registry.row_ids(session, kind) for kind in registry.KINDS}
    clusters = await touched_clusters(session, ids[registry.NEED])
    clusters |= set(ids[registry.CLUSTER])
    removed = {
        registry.FEEDBACK: await remove(session, Feedback, ids[registry.FEEDBACK]),
        registry.SIGNUP: await remove(session, TestSignup, ids[registry.SIGNUP]),
        registry.ADAPTATION: await remove(
            session, Adaptation, ids[registry.ADAPTATION]
        ),
        registry.MESSAGE: await remove(session, Message, ids[registry.MESSAGE]),
    }
    if ids[registry.ADMIN]:
        result = await session.exec(
            delete(AdminAction).where(
                col(AdminAction.admin_id).in_(ids[registry.ADMIN])
            )
        )
        removed["admin_action"] = result.rowcount or 0
    removed[registry.NEED] = await remove(session, Need, ids[registry.NEED])
    removed[registry.IDEA] = await remove(session, Idea, ids[registry.IDEA])
    await session.flush()
    deleted, kept = await settle_clusters(session, clusters, set(ids[registry.CLUSTER]))
    removed[registry.CLUSTER] = deleted
    removed[registry.ADMIN] = await remove(session, AdminUser, ids[registry.ADMIN])
    await session.exec(delete(DemoRecord))
    await session.commit()
    for cluster_id in kept:
        try:
            await refresh_cluster_summary(cluster_id)
        except AiUnavailableError:
            console.print(f"[yellow]summary of cluster {cluster_id} left stale[/]")
    removed["clusters_kept"] = len(kept)
    return removed


async def run() -> int:
    setup_logging()
    try:
        await init_db()
        async with session_scope() as session:
            before = await registry.counts(session)
            if not sum(before.values()):
                console.print("no demo rows, nothing to wipe")
                return 0
            removed = await wipe(session)
            after = await registry.counts(session)
    finally:
        await container.close()
    console.print("[bold]removed[/]")
    for kind, total in removed.items():
        console.print(f"  {kind:<14} {total:>4}")
    console.print(f"demo rows left: {sum(after.values())}")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
