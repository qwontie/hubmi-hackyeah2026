import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Executable, Result, Row, text
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.knowledge.map import PROBLEM_MIN_NEEDS
from utils.db.models.idea import Idea, IdeaStatus
from utils.db.models.innovation import Innovation

INNOVATIONS_LIMIT = 5
IDEAS_LIMIT = 20

PROBLEMS_SQL = """
WITH stats AS (
    SELECT
        cluster_id,
        count(*) AS needs_total,
        count(*) FILTER (WHERE status = 'new') AS needs_open,
        count(*) FILTER (WHERE status <> 'new') AS needs_answered
    FROM need
    WHERE cluster_id IS NOT NULL
    GROUP BY cluster_id
    HAVING count(*) >= :min_needs
),
places AS (
    SELECT cluster_id, array_agg(powiat ORDER BY needs DESC, powiat) AS powiats
    FROM (
        SELECT cluster_id, powiat, count(*) AS needs
        FROM need
        WHERE cluster_id IS NOT NULL AND powiat IS NOT NULL
        GROUP BY cluster_id, powiat
        HAVING count(*) >= :min_needs
    ) per_powiat
    GROUP BY cluster_id
),
ideas AS (
    SELECT problem_id, count(*) AS ideas_count
    FROM idea
    WHERE status = 'accepted' AND problem_id IS NOT NULL
    GROUP BY problem_id
)
SELECT
    c.id,
    c.title,
    c.summary,
    c.category_slug,
    cat.name AS category_name,
    c.last_need_at,
    s.needs_total,
    s.needs_open,
    s.needs_answered,
    coalesce(i.ideas_count, 0) AS ideas_count,
    coalesce(p.powiats, ARRAY[]::text[]) AS powiats
FROM need_cluster c
JOIN stats s ON s.cluster_id = c.id
LEFT JOIN places p ON p.cluster_id = c.id
LEFT JOIN ideas i ON i.problem_id = c.id
LEFT JOIN category cat ON cat.slug = c.category_slug
WHERE {where}
"""

COUNT_SQL = "SELECT count(*) FROM ({query}) problems"
PAGE_SQL = """
SELECT * FROM ({query}) problems
ORDER BY needs_open DESC, needs_total DESC, last_need_at DESC NULLS LAST, id
LIMIT :limit OFFSET :offset
"""

MATCHED_SQL = text("""
SELECT mr.innovation_id
FROM match_result mr
JOIN need n ON n.id = mr.need_id
JOIN innovation inn ON inn.id = mr.innovation_id
WHERE n.cluster_id = :id AND inn.status = 'published'
GROUP BY mr.innovation_id
ORDER BY count(DISTINCT mr.need_id) DESC, avg(mr.score) DESC
LIMIT :limit
""")


@dataclass(frozen=True, slots=True)
class ProblemFilters:
    q: str | None = None
    category: str | None = None
    powiat: str | None = None


@dataclass(frozen=True, slots=True)
class ProblemRow:
    id: uuid.UUID
    title: str
    summary: str
    category_slug: str | None
    category_name: str | None
    needs_total: int
    needs_open: int
    needs_answered: int
    ideas_count: int
    powiats: list[str]


async def run(
    session: AsyncSession, statement: Executable, params: dict[str, Any]
) -> Result[Any]:
    connection = await session.connection()
    return await connection.execute(statement, params)


def _like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _where(filters: ProblemFilters) -> tuple[str, dict[str, Any]]:
    clauses = ["TRUE"]
    params: dict[str, Any] = {"min_needs": PROBLEM_MIN_NEEDS}
    if filters.category:
        clauses.append("c.category_slug = :category")
        params["category"] = filters.category
    if filters.powiat:
        clauses.append(":powiat = ANY(p.powiats)")
        params["powiat"] = filters.powiat
    if filters.q:
        clauses.append(
            "(c.title ILIKE :q ESCAPE '\\' OR c.summary ILIKE :q ESCAPE '\\')"
        )
        params["q"] = _like(filters.q)
    return " AND ".join(clauses), params


def _row(row: Row[Any]) -> ProblemRow:
    return ProblemRow(
        id=row.id,
        title=row.title,
        summary=row.summary,
        category_slug=row.category_slug,
        category_name=row.category_name,
        needs_total=row.needs_total,
        needs_open=row.needs_open,
        needs_answered=row.needs_answered,
        ideas_count=row.ideas_count,
        powiats=list(row.powiats),
    )


async def list_problems(
    session: AsyncSession, filters: ProblemFilters, *, page: int, per_page: int
) -> tuple[list[ProblemRow], int]:
    where, params = _where(filters)
    query = PROBLEMS_SQL.format(where=where)
    total = (
        await run(session, text(COUNT_SQL.format(query=query)), params)
    ).scalar_one()
    rows = (
        await run(
            session,
            text(PAGE_SQL.format(query=query)),
            {**params, "limit": per_page, "offset": (page - 1) * per_page},
        )
    ).all()
    return [_row(row) for row in rows], int(total)


async def get_problem(
    session: AsyncSession, problem_id: uuid.UUID
) -> ProblemRow | None:
    where, params = _where(ProblemFilters())
    row = (
        await run(
            session,
            text(PROBLEMS_SQL.format(where=f"{where} AND c.id = :id")),
            {**params, "id": problem_id},
        )
    ).first()
    return _row(row) if row is not None else None


async def problem_innovations(
    session: AsyncSession, problem_id: uuid.UUID
) -> list[Innovation]:
    ids = list(
        (
            await run(
                session, MATCHED_SQL, {"id": problem_id, "limit": INNOVATIONS_LIMIT}
            )
        ).scalars()
    )
    if not ids:
        return []
    rows = (
        await session.exec(select(Innovation).where(col(Innovation.id).in_(ids)))
    ).all()
    by_id = {row.id: row for row in rows}
    return [by_id[i] for i in ids if i in by_id]


async def problem_ideas(session: AsyncSession, problem_id: uuid.UUID) -> list[Idea]:
    return list(
        (
            await session.exec(
                select(Idea)
                .where(
                    col(Idea.problem_id) == problem_id,
                    col(Idea.status) == IdeaStatus.ACCEPTED,
                )
                .order_by(col(Idea.created_at).desc())
                .limit(IDEAS_LIMIT)
            )
        ).all()
    )
