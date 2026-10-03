import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlmodel import col, select

from dependencies.container import container
from services.needs import merge_clusters, refresh_cluster_summary
from services.needs.clusters import TITLE_SIMILARITY, fill_title_vectors
from utils.db import init_db, session_scope
from utils.db.models.need import NeedCluster

console = Console()


def rank(cluster: NeedCluster) -> tuple[bool, int, datetime, str]:
    return (
        not cluster.title_locked,
        -cluster.size,
        cluster.created_at,
        str(cluster.id),
    )


def similarity(a: NeedCluster, b: NeedCluster) -> float:
    return sum(
        x * y
        for x, y in zip(a.title_embedding or [], b.title_embedding or [], strict=True)
    )


Merge = tuple[NeedCluster, list[tuple[NeedCluster, float]]]


async def plan(threshold: float) -> list[Merge]:
    async with session_scope() as session:
        while (
            await session.exec(
                select(NeedCluster.id).where(
                    col(NeedCluster.title_embedding).is_(None),
                    col(NeedCluster.size) > 0,
                )
            )
        ).first():
            await fill_title_vectors(session)
        await session.commit()
        clusters = sorted(
            await session.exec(select(NeedCluster).where(col(NeedCluster.size) > 0)),
            key=rank,
        )
    taken: set[str] = set()
    merges: list[Merge] = []
    for target in clusters:
        if str(target.id) in taken:
            continue
        taken.add(str(target.id))
        sources = [
            (other, score)
            for other in clusters
            if str(other.id) not in taken
            and (score := similarity(target, other)) >= threshold
        ]
        taken.update(str(other.id) for other, _ in sources)
        if sources:
            merges.append((target, sources))
    return merges


async def run(*, apply: bool, threshold: float) -> None:
    await init_db()
    try:
        merges = await plan(threshold)
        moved = sum(len(sources) for _, sources in merges)
        for target, sources in merges:
            console.print(f"[bold]{target.title}[/] ({target.size})")
            for source, score in sources:
                console.print(f"    <- {source.title} ({source.size}) {score:.3f}")
        console.print(
            f"{len(merges)} groups absorb {moved} others at title similarity "
            f">= {threshold}"
        )
        if not apply:
            console.print("dry run, nothing merged; add --apply to merge")
            return
        for target, sources in merges:
            for source, _ in sources:
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
