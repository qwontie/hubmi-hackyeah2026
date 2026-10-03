import argparse
import asyncio
import sys
from pathlib import Path

from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pydantic import BaseModel, ValidationError

from dependencies.container import container
from services.auth.admins import AdminRepository
from services.auth.schemas import Login, Password
from utils.db import init_db, session_scope

console = Console()


class Args(BaseModel):
    login: Login
    password: Password


def parse() -> Args:
    parser = argparse.ArgumentParser(
        description="Create an admin or reset its password"
    )
    parser.add_argument("login")
    parser.add_argument("password")
    raw = parser.parse_args()
    try:
        return Args(login=raw.login, password=raw.password)
    except ValidationError as exc:
        console.print("[bold red]✗ Invalid arguments[/]")
        for error in exc.errors():
            loc = ".".join(str(part) for part in error["loc"])
            console.print(f"  [red]{loc}[/]: {error['msg']}")
        raise SystemExit(1) from exc


async def run(args: Args) -> None:
    try:
        await init_db()
        async with session_scope() as session:
            admin, created = await AdminRepository(session).upsert(
                args.login, args.password
            )
    finally:
        await container.close()
    verb = "created" if created else "password updated"
    console.print(f"[green]✓[/] admin [bold]{admin.login}[/] {verb}")


def main() -> None:
    asyncio.run(run(parse()))


if __name__ == "__main__":
    main()
