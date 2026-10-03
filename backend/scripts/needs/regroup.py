import argparse
import asyncio
import sys
import uuid
from pathlib import Path

from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlmodel import col, select

from dependencies.container import container
from services.needs import merge_clusters, refresh_cluster_summary
from services.needs.clusters import TITLE_SIMILARITY, fill_title_vectors
from services.search.vector import cosine_distance
from utils.db import init_db, session_scope
from utils.db.models.need import NeedCluster

console = Console()


class Groups:
    def __init__(self, ids: list[uuid.UUID]) -> None:
        self.parent = {cluster_id: cluster_id for cluster_id in ids}

    def find(self, cluster_id: uuid.UUID) -> uuid.UUID:
        while self.parent[cluster_id] != cluster_id:
            self.parent[cluster_id] = self.parent[self.parent[cluster_id]]
            cluster_id = self.parent[cluster_id]
        return cluster_id

    def join(self, a: uuid.UUID, b: uuid.UUID) -> None:
        self.parent[self.find(a)] = self.find(b)


def keeper(members: list[NeedCluster]) -> NeedCluster:
    return min(
        members, key=lambda c: (not c.title_locked, -c.size, c.created_at, str(c.id))
    )


async def plan(threshold: float) -> list[tuple[NeedCluster, list[NeedCluster]]]:
    async with session_scope() as session:
        while True:
            before = (
                await session.exec(
                    select(NeedCluster.id).where(
                        col(NeedCluster.title_embedding).is_(None),
                        col(NeedCluster.size) > 0,
                    )
                )
            ).all()
            if not before:
                break
            await fill_title_vectors(session)
        await session.commit()
        clusters = list(
            await session.exec(select(NeedCluster).where(col(NeedCluster.size) > 0))
        )
        groups = Groups([c.id for c in clusters])
        for cluster in clusters:
            vector = list(cluster.title_embedding or [])
            distance = cosine_distance(NeedCluster.title_embedding, vector)
            near = (
                await session.exec(
                    select(NeedCluster.id, distance).where(
                        col(NeedCluster.id) != cluster.id,
                        col(NeedCluster.size) > 0,
                        distance <= 1 - threshold,
                    )
                )
            ).all()
            for other_id, _ in near:
                groups.join(cluster.id, other_id)
    components: dict[uuid.UUID, list[NeedCluster]] = {}
    for cluster in clusters:
        components.setdefault(groups.find(cluster.id), []).append(cluster)
    merges = []
    for members in components.values():
        if len(members) < 2:  # noqa: PLR2004
            continue
        target = keeper(members)
        merges.append((target, [c for c in members if c.id != target.id]))
    return sorted(merges, key=lambda m: -sum(c.size for c in m[1]) - m[0].size)


async def run(*, apply: bool, threshold: float) -> None:
    await init_db()
    try:
        merges = await plan(threshold)
        moved = sum(len(sources) for _, sources in merges)
        for target, sources in merges:
            console.print(f"[bold]{target.title}[/] ({target.size})")
            for source in sources:
                console.print(f"    <- {source.title} ({source.size})")
        console.print(
            f"{len(merges)} groups absorb {moved} others at title similarity "
            f">= {threshold}"
        )
        if not apply:
            console.print("dry run, nothing merged; add --apply to merge")
            return
        for target, sources in merges:
            for source in sources:
                async with session_scope() as session:
                    await merge_clusters(session, source.id, target.id)
        for target, _ in merges:
            await refresh_cluster_summary(target.id)
        console.print(f"[green]merged {moved} groups into {len(merges)}[/]")
    finally:
        await container.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge need groups whose titles mean the same problem"
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--threshold", type=float, default=TITLE_SIMILARITY)
    args = parser.parse_args()
    asyncio.run(run(apply=args.apply, threshold=args.threshold))


if __name__ == "__main__":
    main()
