import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlmodel import col, select

from dependencies.container import container
from services.ai import AiBudgetExceededError, AiUnavailableError
from services.ai.costs import budget_limit, spent_last_day
from services.library.images.pictures import UnusableImageError
from services.library.images.service import find_image, spent_since, store
from services.library.images.sources import client
from utils.db import init_db, session_scope
from utils.db.models import Innovation
from utils.logging import setup_logging

console = Console()


def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Give every innovation one picture: a photo from its ROPS brochure, "
            "its video thumbnail, or a generated illustration"
        )
    )
    parser.add_argument("--limit", type=int, default=None, help="process at most N")
    parser.add_argument("--slug", action="append", default=[], help="only this slug")
    parser.add_argument(
        "--force", action="store_true", help="redo innovations that have a picture"
    )
    parser.add_argument(
        "--no-generate",
        action="store_true",
        help="use only ROPS photos and video thumbnails",
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=8.0,
        help="stop when this run has spent this many USD on AI",
    )
    parser.add_argument(
        "--reserve",
        type=float,
        default=0.5,
        help="leave this many USD of the batch daily AI budget",
    )
    return parser.parse_args()


async def targets(args: argparse.Namespace) -> list[Innovation]:
    query = select(Innovation).order_by(col(Innovation.slug))
    if args.slug:
        query = query.where(col(Innovation.slug).in_(args.slug))
    if not args.force:
        query = query.where(col(Innovation.image_version).is_(None))
    async with session_scope() as session:
        rows = list((await session.exec(query)).all())
    return rows[: args.limit] if args.limit else rows


async def process(args: argparse.Namespace) -> int:
    started = datetime.now(UTC)
    todo = await targets(args)
    console.print(f"[bold]{len(todo)}[/] innovations without a picture")
    counts: dict[str, int] = {}
    failed = 0
    async with client() as http:
        for index, innovation in enumerate(todo, 1):
            async with session_scope() as session:
                spent = await spent_since(session, started)
            if spent >= args.budget:
                console.print(f"[red]budget reached[/] ${spent:.4f}")
                break
            if budget_limit() - await spent_last_day() < args.reserve:
                console.print("[red]daily AI budget is nearly used, run again later[/]")
                break
            try:
                chosen = await find_image(
                    http, innovation, generate=not args.no_generate
                )
            except AiBudgetExceededError:
                console.print("[red]daily AI budget reached, run again later[/]")
                break
            except (AiUnavailableError, UnusableImageError) as e:
                failed += 1
                console.print(f"[red]x[/] {innovation.slug}: {e!r}")
                continue
            if chosen is None:
                console.print(f"[dim]{index:>3}/{len(todo)}[/] {innovation.slug}: none")
                continue
            async with session_scope() as session:
                version = await store(session, innovation.id, chosen)
            counts[chosen.source.value] = counts.get(chosen.source.value, 0) + 1
            console.print(
                f"[dim]{index:>3}/{len(todo)}[/] {innovation.slug}: "
                f"[green]{chosen.source.value}[/] v{version} {chosen.alt}"
            )
    async with session_scope() as session:
        spent = await spent_since(session, started)
    summary = " ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    console.print(f"[bold]done[/] {summary} failed={failed} spent=${spent:.4f}")
    return 1 if failed else 0


async def run(args: argparse.Namespace) -> int:
    setup_logging()
    try:
        await init_db()
        return await process(args)
    finally:
        await container.close()


def main() -> None:
    raise SystemExit(asyncio.run(run(parse())))


if __name__ == "__main__":
    main()
