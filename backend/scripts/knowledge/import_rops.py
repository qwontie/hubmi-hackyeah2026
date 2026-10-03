import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dependencies.container import container
from services.knowledge import STEPS, run_knowledge_import
from utils.db import init_db
from utils.db.models import ImportTrigger
from utils.logging import setup_logging

console = Console()


def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import ROPS reports, publications and guides, extract the social "
            "challenges and the powiat figures into the database"
        )
    )
    parser.add_argument(
        "--steps",
        nargs="+",
        choices=STEPS,
        default=list(STEPS),
        help="which steps to run, in order",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="keep downloaded files here and reuse them on the next run",
    )
    parser.add_argument(
        "--delay", type=float, default=1.0, help="seconds between requests"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="download and extract every file again; summaries stay cached by hash",
    )
    return parser.parse_args()


def show(payload: dict[str, Any]) -> None:
    counters = payload["counters"]
    short = " ".join(
        f"{key}={value}" for key, value in counters.items() if key != "errors"
    )
    console.print(
        f"[dim]{payload['step']} {payload['done']:>3}/{payload['total']}[/] "
        f"{payload['current'][:70]}  {short}"
    )


async def run(args: argparse.Namespace) -> int:
    setup_logging()
    try:
        await init_db()
        result = await run_knowledge_import(
            trigger=ImportTrigger.SCRIPT,
            steps=tuple(args.steps),
            cache_dir=args.cache_dir,
            delay=args.delay,
            force=args.force,
            progress=show,
        )
    finally:
        await container.close()
    console.print(f"[bold]{result.status.value}[/] {result.counters}")
    if result.error:
        console.print(f"[red]{result.error}[/]")
        return 1
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run(parse())))


if __name__ == "__main__":
    main()
