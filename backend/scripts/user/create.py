import argparse
import asyncio
import sys
from pathlib import Path

from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pydantic import BaseModel, Field, ValidationError, model_validator

from dependencies.container import container
from services.auth.admins import AdminRepository, Profile
from services.auth.schemas import Login, Password
from services.modules import normalize_email
from utils.db import init_db, session_scope
from utils.db.models import AdminRole

console = Console()


class Args(BaseModel):
    login: Login
    password: Password
    role: AdminRole = AdminRole.ADMIN
    name: str | None = Field(default=None, min_length=2, max_length=120)
    expertise: str | None = Field(default=None, min_length=2, max_length=200)
    email: str | None = Field(default=None, max_length=254)

    @model_validator(mode="after")
    def expert_profile(self) -> "Args":
        if self.role == AdminRole.EXPERT and not (self.name and self.expertise):
            message = "an expert needs --name and --expertise"
            raise ValueError(message)
        if self.email is not None:
            email = normalize_email(self.email)
            if email is None:
                message = "--email is not a valid address"
                raise ValueError(message)
            self.email = email
        return self


def parse() -> Args:
    parser = argparse.ArgumentParser(
        description="Create an admin or an expert, or reset the password"
    )
    parser.add_argument("login")
    parser.add_argument("password")
    parser.add_argument("--role", choices=[role.value for role in AdminRole])
    parser.add_argument("--name", help="display name shown to authors (experts)")
    parser.add_argument("--expertise", help="field of expertise (experts)")
    parser.add_argument("--email", help="address for assignment mail")
    raw = parser.parse_args()
    try:
        return Args.model_validate(
            {
                key: value
                for key, value in {
                    "login": raw.login,
                    "password": raw.password,
                    "role": raw.role,
                    "name": raw.name,
                    "expertise": raw.expertise,
                    "email": raw.email,
                }.items()
                if value is not None
            }
        )
    except ValidationError as exc:
        console.print("[bold red]✗ Invalid arguments[/]")
        for error in exc.errors():
            loc = ".".join(str(part) for part in error["loc"]) or "args"
            console.print(f"  [red]{loc}[/]: {error['msg']}")
        raise SystemExit(1) from exc


def profile_of(args: Args, *, explicit: bool) -> Profile | None:
    if not explicit:
        return None
    return Profile(
        role=args.role,
        display_name=args.name,
        expertise=args.expertise,
        email=args.email,
    )


async def run(args: Args, *, explicit: bool) -> None:
    try:
        await init_db()
        async with session_scope() as session:
            admin, created = await AdminRepository(session).upsert(
                args.login, args.password, profile_of(args, explicit=explicit)
            )
    finally:
        await container.close()
    verb = "created" if created else "updated"
    console.print(f"[green]✓[/] {admin.role} [bold]{admin.login}[/] {verb}")


def main() -> None:
    flags = ("--role", "--name", "--expertise", "--email")
    explicit = any(arg.split("=", 1)[0] in flags for arg in sys.argv)
    asyncio.run(run(parse(), explicit=explicit))


if __name__ == "__main__":
    main()
