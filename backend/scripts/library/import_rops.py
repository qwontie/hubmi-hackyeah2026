import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dependencies.container import container
from services.ingest import run_import
from utils.db import init_db
from utils.db.models import ImportTrigger
from utils.logging import setup_logging

console = Console()


def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import the ROPS social innovation library into the database"
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="keep raw HTML here and reuse it on the next run",
    )
    parser.add_argument(
        "--delay", type=float, default=1.0, help="seconds between requests"
    )
    return parser.parse_args()


def show(payload: dict[str, Any]) -> None:
    console.print(
        f"[dim]{payload['done']:>3}/{payload['total']}[/] {payload['current']}"
        f"  [green]+{payload['created']}[/] [yellow]~{payload['updated']}[/]"
        f" [red]x{payload['failed']}[/]"
    )


async def run(args: argparse.Namespace) -> int:
    setup_logging()
    try:
        await init_db()
        result = await run_import(
            trigger=ImportTrigger.SCRIPT,
            cache_dir=args.cache_dir,
            delay=args.delay,
            progress=show,
        )
    finally:
        await container.close()
    console.print(
        f"[bold]{result.status.value}[/] total={result.total} created={result.created}"
        f" updated={result.updated} unchanged={result.unchanged}"
        f" skipped_edited={result.skipped_edited} failed={result.failed}"
    )
    if result.error:
        console.print(f"[red]{result.error}[/]")
        return 1
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run(parse())))


if __name__ == "__main__":
    main()
