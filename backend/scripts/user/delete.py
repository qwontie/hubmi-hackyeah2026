import argparse
import asyncio
import sys
from pathlib import Path

from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dependencies.container import container
from services.auth.admins import AdminRepository
from utils.db import init_db, session_scope

console = Console()


async def run(login: str) -> None:
    try:
        await init_db()
        async with session_scope() as session:
            deleted = await AdminRepository(session).delete(login)
    finally:
        await container.close()
    if not deleted:
        console.print(f"[red]✗[/] no admin [bold]{login}[/]")
        raise SystemExit(1)
    console.print(f"[green]✓[/] admin [bold]{login}[/] deleted")


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete an admin")
    parser.add_argument("login")
    asyncio.run(run(parser.parse_args().login))


if __name__ == "__main__":
    main()
