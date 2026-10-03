import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from rich.console import Console

from dependencies.container import container
from scripts.demo import registry
from services.experts.by_email import answer_url
from utils.db import init_db, session_scope
from utils.db.models import Assignment, Need
from utils.logging import setup_logging

console = Console()

KEY = "expert-link"
EMAIL = "ekspertka.demo@example.org"
NOTE = (
    "Czy to rozwiązanie da się wprowadzić w małej gminie? "
    "Od czego zacząć i z kim rozmawiać?"
)


async def run() -> int:
    setup_logging()
    try:
        await init_db()
        async with session_scope() as session:
            known = await registry.lookup(session, registry.ASSIGNMENT, KEY)
            assignment = await session.get(Assignment, known) if known else None
            if assignment is None:
                need_ids = await registry.row_ids(session, registry.NEED)
                need = None
                for need_id in need_ids:
                    need = await session.get(Need, need_id)
                    if need is not None:
                        break
                if need is None:
                    console.print("[red]no demo need found, load the demo first[/]")
                    return 1
                assignment = Assignment(
                    need_id=need.id,
                    expert_email=EMAIL,
                    expert_name="Anna Nowak",
                    expert_field="Usługi opiekuńcze",
                    note=NOTE,
                    assigned_by="demo",
                    delivery_status="skipped",
                )
                session.add(assignment)
                await session.commit()
                await session.refresh(assignment)
                await registry.register(
                    session, registry.ASSIGNMENT, KEY, assignment.id
                )
            print(answer_url(assignment.id))
    finally:
        await container.close()
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
