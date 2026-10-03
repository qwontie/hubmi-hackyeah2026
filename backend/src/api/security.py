from typing import Annotated

from fastapi import Depends, HTTPException, status
from starlette.requests import HTTPConnection

from services.auth.crypto import session_admin_id
from utils.db import session_scope
from utils.db.models import AdminUser
from utils.env import env


async def admin_from_secret(secret: str | None) -> AdminUser | None:
    if not secret:
        return None
    admin_id = session_admin_id(secret)
    if admin_id is None:
        return None
    async with session_scope() as session:
        return await session.get(AdminUser, admin_id)


async def current_admin(conn: HTTPConnection) -> AdminUser:
    admin = await admin_from_secret(conn.cookies.get(env.auth.cookie_name))
    if admin is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return admin


AdminPerson = Annotated[AdminUser, Depends(current_admin)]
