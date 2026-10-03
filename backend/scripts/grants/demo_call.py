import argparse
import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import delete
from sqlmodel import col, select

from dependencies.container import container
from services.grants.templates import ROPS_CALL_URL, ROPS_INNOVATION
from utils.db import init_db, session_scope
from utils.db.models import GrantApplication, GrantCall, GrantCallStatus

console = Console()

TITLE = "Nabór pokazowy: granty na pomysły na innowacje społeczne"
DESCRIPTION = (
    "To jest nabór pokazowy HubMi, nie prawdziwy nabór ROPS. Pokazuje, jak "
    "pomysł z Kreatora zamienia się w wniosek dopasowany do pytań naboru.\n\n"
    "Pytania pochodzą z publicznego formularza aplikacyjnego ROPS w Krakowie "
    "dla pomysłów na innowacje społeczne. Wniosek złożony tutaj nie trafia do "
    "prawdziwej oceny."
)


def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or remove the demo grant call (clearly marked as demo)"
    )
    parser.add_argument("--days", type=int, default=14, help="how long it stays open")
    parser.add_argument(
        "--wipe", action="store_true", help="remove demo calls and their applications"
    )
    return parser.parse_args()


async def wipe() -> None:
    async with session_scope() as session:
        ids = list(
            (await session.exec(select(GrantCall.id).where(col(GrantCall.demo)))).all()
        )
        if ids:
            await session.exec(
                delete(GrantApplication).where(col(GrantApplication.call_id).in_(ids))
            )
            await session.exec(delete(GrantCall).where(col(GrantCall.id).in_(ids)))
            await session.commit()
    console.print(f"[green]✓[/] removed {len(ids)} demo call(s)")


async def create(days: int) -> None:
    now = datetime.now(UTC)
    async with session_scope() as session:
        existing = (
            await session.exec(select(GrantCall).where(col(GrantCall.demo)))
        ).first()
        if existing is not None:
            console.print(f"[yellow]•[/] demo call already exists: {existing.id}")
            return
        call = GrantCall(
            title=TITLE,
            description=DESCRIPTION,
            opens_at=now - timedelta(minutes=1),
            closes_at=now + timedelta(days=days),
            status=GrantCallStatus.PUBLISHED,
            source_url=ROPS_CALL_URL,
            sections=[s.model_dump() for s in ROPS_INNOVATION.sections],
            template=ROPS_INNOVATION.slug,
            demo=True,
            notified_open_at=now,
        )
        session.add(call)
        await session.commit()
        await session.refresh(call)
    console.print(
        f"[green]✓[/] demo call {call.id} open until {call.closes_at:%Y-%m-%d}"
    )


async def run(args: argparse.Namespace) -> None:
    try:
        await init_db()
        if args.wipe:
            await wipe()
        else:
            await create(max(1, min(args.days, 90)))
    finally:
        await container.close()


def main() -> None:
    asyncio.run(run(parse()))


if __name__ == "__main__":
    main()
