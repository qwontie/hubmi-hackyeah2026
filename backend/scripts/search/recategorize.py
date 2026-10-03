import argparse
import asyncio
import sys
from collections import Counter
from pathlib import Path

from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlmodel import col, select

from dependencies.container import container
from services.search import category_for
from utils.db import init_db, session_scope
from utils.db.models.need import Need, NeedCluster

console = Console()


async def run(*, apply: bool) -> None:
    await init_db()
    try:
        async with session_scope() as session:
            needs = (
                await session.exec(select(Need).where(col(Need.embedding).is_not(None)))
            ).all()
            changed = 0
            for need in needs:
                category = await category_for(session, list(need.embedding or []))
                if category and category != need.category_slug:
                    changed += 1
                    need.category_slug = category
                    session.add(need)
            console.print(f"needs: {changed} of {len(needs)} get a new category")
            await session.flush()
            clusters = (await session.exec(select(NeedCluster))).all()
            for cluster in clusters:
                members = (
                    await session.exec(
                        select(Need.category_slug).where(
                            col(Need.cluster_id) == cluster.id
                        )
                    )
                ).all()
                votes = Counter(slug for slug in members if slug)
                category = votes.most_common(1)[0][0] if votes else None
                if category and category != cluster.category_slug:
                    console.print(
                        f"group [bold]{cluster.title}[/]: "
                        f"{cluster.category_slug} -> {category}"
                    )
                    cluster.category_slug = category
                    session.add(cluster)
            if apply:
                await session.commit()
                console.print("[green]saved[/]")
            else:
                await session.rollback()
                console.print("dry run, nothing saved; add --apply to save")
    finally:
        await container.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recompute need and group categories from need embeddings"
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(apply=args.apply))


if __name__ == "__main__":
    main()
