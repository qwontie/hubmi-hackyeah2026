from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, status
from starlette.requests import HTTPConnection

from services.auth.crypto import session_claims
from utils.db import session_scope
from utils.db.models import AdminRole, AdminSession, AdminUser
from utils.env import env


async def admin_from_secret(secret: str | None) -> AdminUser | None:
    if not secret:
        return None
    claims = session_claims(secret)
    if claims is None:
        return None
    async with session_scope() as session:
        admin = await session.get(AdminUser, claims.admin_id)
        if admin is None or admin.token_version != claims.token_version:
            return None
        auth_session = await session.get(AdminSession, claims.session_id)
        if (
            auth_session is None
            or auth_session.admin_id != admin.id
            or auth_session.expires_at <= datetime.now(UTC)
        ):
            return None
        return admin


async def current_staff(conn: HTTPConnection) -> AdminUser:
    admin = await admin_from_secret(conn.cookies.get(env.auth.cookie_name))
    if admin is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return admin


async def current_admin(conn: HTTPConnection) -> AdminUser:
    admin = await current_staff(conn)
    if admin.role != AdminRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return admin


async def current_expert(conn: HTTPConnection) -> AdminUser:
    admin = await current_staff(conn)
    if admin.role != AdminRole.EXPERT:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return admin


AdminPerson = Annotated[AdminUser, Depends(current_admin)]
StaffPerson = Annotated[AdminUser, Depends(current_staff)]
ExpertPerson = Annotated[AdminUser, Depends(current_expert)]
