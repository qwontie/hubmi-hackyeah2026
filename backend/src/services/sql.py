from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, Executable, Row, func
from sqlmodel.ext.asyncio.session import AsyncSession


async def fetch(session: AsyncSession, statement: Executable) -> Sequence[Row[Any]]:
    connection = await session.connection()
    return (await connection.execute(statement)).all()


def unaccent_like(column: Any, query: str) -> ColumnElement[bool]:  # noqa: ANN401
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return func.hubmi_unaccent(column).ilike(
        func.hubmi_unaccent(f"%{escaped}%"), escape="\\"
    )
