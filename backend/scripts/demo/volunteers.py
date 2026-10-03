import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import httpx
from pydantic import SecretStr
from rich.console import Console

from dependencies.container import container
from scripts.demo.load import Run, load_demand, load_signups, read
from services.mail import Mailer
from utils.db import init_db, session_scope
from utils.env import MailSettings
from utils.logging import setup_logging

console = Console()


async def run() -> int:
    setup_logging()
    modules = read("modules.json")
    try:
        await init_db()
        async with session_scope() as session, httpx.AsyncClient() as client:
            state = Run(
                session=session,
                now=datetime.now(UTC),
                admins=[],
                mailer=Mailer(MailSettings(resend_api_key=SecretStr("")), client),
            )
            await load_signups(state, modules["test_signups"])
            await load_demand(state, modules["demand"])
            console.print(f"demo volunteers and demand: {state.created}")
            for warning in state.warnings:
                console.print(f"[yellow]warning[/] {warning}")
    finally:
        await container.close()
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
