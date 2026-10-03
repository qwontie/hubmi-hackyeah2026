import uuid
from dataclasses import dataclass

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.auth.crypto import hash_password_async, verify_password
from utils.db.models import AdminRole, AdminUser


@dataclass(frozen=True, slots=True)
class Profile:
    role: AdminRole
    display_name: str | None = None
    expertise: str | None = None
    email: str | None = None


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, admin_id: uuid.UUID) -> AdminUser | None:
        return await self.session.get(AdminUser, admin_id)

    async def by_login(self, login: str) -> AdminUser | None:
        result = await self.session.exec(
            select(AdminUser).where(col(AdminUser.login) == login.strip().lower())
        )
        return result.first()

    async def verify(self, login: str, password: str) -> AdminUser | None:
        admin = await self.by_login(login)
        if admin is None or not await verify_password(password, admin.password_hash):
            return None
        return admin

    async def save(self, admin: AdminUser) -> AdminUser:
        self.session.add(admin)
        await self.session.commit()
        await self.session.refresh(admin)
        return admin

    async def upsert(
        self, login: str, password: str, profile: Profile | None = None
    ) -> tuple[AdminUser, bool]:
        admin = await self.by_login(login)
        created = admin is None
        if admin is None:
            admin = AdminUser(login=login, password_hash="")
        admin.password_hash = await hash_password_async(password)
        if not created:
            admin.token_version += 1
        if profile is not None:
            admin.role = profile.role
            admin.display_name = profile.display_name
            admin.expertise = profile.expertise
            admin.email = profile.email
        return await self.save(admin), created

    async def delete(self, login: str) -> bool:
        admin = await self.by_login(login)
        if admin is None:
            return False
        await self.session.delete(admin)
        await self.session.commit()
        return True
