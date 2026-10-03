import uuid

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.auth.crypto import hash_password, verify_password
from utils.db.models import AdminUser


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
        if admin is None or not verify_password(password, admin.password_hash):
            return None
        return admin

    async def save(self, admin: AdminUser) -> AdminUser:
        self.session.add(admin)
        await self.session.commit()
        await self.session.refresh(admin)
        return admin

    async def upsert(self, login: str, password: str) -> tuple[AdminUser, bool]:
        admin = await self.by_login(login)
        created = admin is None
        if admin is None:
            admin = AdminUser(login=login, password_hash="")
        admin.password_hash = hash_password(password)
        return await self.save(admin), created

    async def delete(self, login: str) -> bool:
        admin = await self.by_login(login)
        if admin is None:
            return False
        await self.session.delete(admin)
        await self.session.commit()
        return True
