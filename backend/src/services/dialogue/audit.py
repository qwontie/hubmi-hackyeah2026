from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from utils.db.models import AdminAction, AdminUser


def record(
    session: AsyncSession,
    admin: AdminUser,
    action: str,
    *,
    target: tuple[str, object | None],
    details: dict[str, Any] | None = None,
) -> None:
    target_type, target_id = target
    session.add(
        AdminAction(
            admin_id=admin.id,
            admin_login=admin.login,
            action=action,
            target_type=target_type,
            target_id=None if target_id is None else str(target_id),
            details=details or {},
        )
    )
