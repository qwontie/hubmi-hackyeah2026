# ruff: noqa: S608
import argparse
import asyncio
import re
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table as Grid
from sqlalchemy import Result, TextClause, text
from sqlmodel import col, delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dependencies.container import container
from scripts.demo import registry
from services.ai import AiUnavailableError
from services.ai.costs import AiBudgetExceededError
from services.needs import refresh_cluster_summary
from services.needs.clusters import CLUSTER_LOCK_KEY, recompute
from utils.db import init_db, session_scope
from utils.db.models import NeedCluster
from utils.logging import setup_logging

console = Console()

EMAIL = re.compile(r"([\w.+-])[\w.+-]*@([\w-]+(?:\.[\w-]+)+)")
SAMPLES = 3
CLUSTERS = "need_cluster"


def demo_ids(kind: str) -> str:
    return f"(SELECT row_id FROM demo_record WHERE kind = '{kind}')"


def registered(column: str, kind: str) -> str:
    return f"{column} IN {demo_ids(kind)}"


@dataclass(frozen=True)
class Table:
    name: str
    label: str
    sample: str
    demo: str = "false"
    held: str = "false"
    kind: str | None = None
    follows: str | None = None


def own(name: str, kind: str, label: str, sample: str) -> Table:
    return Table(name, label, sample, demo=registered("id", kind), kind=kind)


TABLES = (
    Table(
        "expert_note",
        "id::text",
        "body",
        demo=registered("assignment_id", registry.ASSIGNMENT),
        follows="assignment",
    ),
    own("message", registry.MESSAGE, "id::text", "body"),
    own(
        "assignment",
        registry.ASSIGNMENT,
        "id::text",
        "coalesce(expert_email, '') || ' ' || coalesce(note, '')",
    ),
    Table(
        "match_result",
        "id::text",
        "reason",
        demo=registered("need_id", registry.NEED),
        follows="need",
    ),
    own(
        "feedback",
        registry.FEEDBACK,
        "id::text",
        "kind || ' ' || coalesce(comment, '')",
    ),
    Table(
        "grant_application",
        "id::text",
        "coalesce(contact_email, '') || ' ' || sections::text",
        held=registered("idea_id", registry.IDEA),
        follows="idea",
    ),
    Table(
        "idea_visualisation",
        "idea_id::text || '/' || version",
        "alt",
        demo=registered("idea_id", registry.IDEA),
        follows="idea",
    ),
    own("idea", registry.IDEA, "id::text", "title || ': ' || essence"),
    Table(
        "volunteer_message",
        "id::text",
        "body",
        held=registered("signup_id", registry.SIGNUP),
        follows="test_signup",
    ),
    Table(
        "volunteer_report",
        "id::text",
        "activity",
        demo=registered("signup_id", registry.SIGNUP),
        follows="test_signup",
    ),
    own("test_signup", registry.SIGNUP, "id::text", "contact_email || ' ' || note"),
    own(
        "innovation_demand",
        registry.DEMAND,
        "id::text",
        "powiat || ' ' || coalesce(contact_email, '')",
    ),
    own("adaptation", registry.ADAPTATION, "id::text", "place || ': ' || context"),
    Table("grant_notice_delivery", "id::text", "notice_key"),
    Table("grant_subscriber", "id::text", "email"),
    Table("search_log", "id::text", "outcome"),
    Table("rate_counter", "key_hash", "hits::text"),
    own("need", registry.NEED, "id::text", "text"),
)
NAMES = (*(table.name for table in TABLES), CLUSTERS)


@dataclass
class Count:
    table: str
    total: int
    demo: int
    held: int
    delete: int
    where: str = "false"
    samples: list[tuple[str, str]] = field(default_factory=list)
    note: str = ""
    deleted: int | None = None


def mask(value: str) -> str:
    return EMAIL.sub(r"\1***@\2", " ".join(value.split()))[:60]


async def sql(session: AsyncSession, query: TextClause) -> Result[Any]:
    connection = await session.connection()
    return await connection.execute(query)


async def number(session: AsyncSession, sql: str) -> int:
    return int(await session.scalar(text(sql)) or 0)


async def blocked(session: AsyncSession, include: set[str]) -> set[str]:
    found: set[str] = set()
    for table in TABLES:
        if table.kind is None or table.name in include:
            continue
        kind = await number(
            session, f"SELECT count(*) FROM demo_record WHERE kind = '{table.kind}'"
        )
        if not kind and await number(session, f"SELECT count(*) FROM {table.name}"):
            found.add(table.name)
    return found


async def count_table(
    session: AsyncSession, table: Table, include: set[str], stop: set[str]
) -> Count:
    held, note = table.held, ""
    if table.name in include:
        held = "false"
    elif table.name in stop:
        held, note = "true", "demo rows not in demo_record, kept"
    elif table.follows in stop:
        held, note = "true", f"kept with {table.follows}"
    demo = f"coalesce(({table.demo}), false)"
    hold = f"coalesce(({held}), false)"
    where = f"NOT {demo} AND NOT {hold}"
    total, demo_rows, held_rows, doomed = (
        await sql(
            session,
            text(
                f"SELECT count(*), count(*) FILTER (WHERE {demo}), "
                f"count(*) FILTER (WHERE NOT {demo} AND {hold}), "
                f"count(*) FILTER (WHERE {where}) FROM {table.name}"
            ),
        )
    ).one()
    if held_rows and not note:
        note = "rows on demo items, kept"
    if held_rows and table.name not in include:
        note += f"; --include {table.name} deletes them"
    samples = (
        await sql(
            session,
            text(
                f"SELECT {table.label}, left({table.sample}, 400) FROM {table.name} "
                f"WHERE {where} ORDER BY 1 LIMIT {SAMPLES}"
            ),
        )
    ).all()
    return Count(
        table=table.name,
        total=total,
        demo=demo_rows,
        held=held_rows,
        delete=doomed,
        where=where,
        samples=[(str(key), mask(str(value or ""))) for key, value in samples],
        note=note,
    )


async def count_clusters(session: AsyncSession, need_where: str) -> Count:
    empty = f"""
        NOT EXISTS (
            SELECT 1 FROM need WHERE need.cluster_id = need_cluster.id
            AND NOT ({need_where})
        )
    """
    total, demo_rows, doomed = (
        await sql(
            session,
            text(
                "SELECT count(*), count(*) FILTER (WHERE "
                f"{registered('id', registry.CLUSTER)}), "
                f"count(*) FILTER (WHERE {empty}) FROM need_cluster"
            ),
        )
    ).one()
    resized = await number(
        session,
        f"""
        SELECT count(DISTINCT cluster_id) FROM need
        WHERE ({need_where}) AND cluster_id IS NOT NULL
        AND cluster_id NOT IN (SELECT id FROM need_cluster WHERE {empty})
        """,
    )
    samples = (
        await sql(
            session,
            text(
                f"SELECT id::text, title FROM need_cluster WHERE {empty} "
                f"ORDER BY 1 LIMIT {SAMPLES}"
            ),
        )
    ).all()
    return Count(
        table=CLUSTERS,
        total=total,
        demo=demo_rows,
        held=0,
        delete=doomed,
        samples=[(key, mask(value)) for key, value in samples],
        note=f"groups without needs go; {resized} groups recounted",
    )


async def plan(session: AsyncSession, include: set[str]) -> list[Count]:
    stop = await blocked(session, include)
    counts = [await count_table(session, table, include, stop) for table in TABLES]
    counts.append(await count_clusters(session, counts[-1].where))
    return counts


async def settle_clusters(
    session: AsyncSession, touched: set[uuid.UUID]
) -> list[uuid.UUID]:
    rows = await sql(
        session,
        text(
            "SELECT cluster_id, count(*) FROM need "
            "WHERE cluster_id IS NOT NULL GROUP BY cluster_id"
        ),
    )
    sizes: dict[uuid.UUID, int] = {key: int(total) for key, total in rows.all()}
    kept: list[uuid.UUID] = []
    for cluster in (await session.exec(select(NeedCluster))).all():
        members = sizes.get(cluster.id, 0)
        if not members:
            await session.exec(
                delete(NeedCluster).where(col(NeedCluster.id) == cluster.id)
            )
        elif cluster.id in touched or cluster.size != members:
            await recompute(session, cluster)
            kept.append(cluster.id)
    await session.flush()
    return kept


async def purge(
    session: AsyncSession, include: set[str]
) -> tuple[list[Count], list[uuid.UUID]]:
    await sql(
        session,
        text("SELECT pg_advisory_xact_lock(:key)").bindparams(key=CLUSTER_LOCK_KEY),
    )
    counts = await plan(session, include)
    touched = set(
        (
            await sql(
                session,
                text(
                    "SELECT DISTINCT cluster_id FROM need "
                    f"WHERE ({counts[-2].where}) AND cluster_id IS NOT NULL"
                ),
            )
        ).scalars()
    )
    for count in counts[:-1]:
        await sql(session, text(f"DELETE FROM {count.table} WHERE {count.where}"))
    kept = await settle_clusters(session, touched)
    for count in counts:
        after = await number(session, f"SELECT count(*) FROM {count.table}")
        count.deleted = count.total - after
    await session.commit()
    return counts, kept


def show(counts: list[Count], *, applied: bool) -> None:
    grid = Grid(title="deleted" if applied else "dry run, nothing changed")
    for column in (
        "table",
        "total",
        "demo",
        "kept",
        "deleted" if applied else "delete",
    ):
        grid.add_column(column, justify="left" if column == "table" else "right")
    for count in counts:
        gone = count.deleted if applied and count.deleted is not None else count.delete
        grid.add_row(
            count.table, str(count.total), str(count.demo), str(count.held), str(gone)
        )
    console.print(grid)
    for count in counts:
        if count.note:
            console.print(f"[yellow]{count.table}[/]: {count.note}")
        for key, value in count.samples:
            console.print(
                f"  {count.table} {key} {value}", markup=False, soft_wrap=True
            )


async def refresh(kept: list[uuid.UUID]) -> None:
    for cluster_id in kept:
        try:
            await refresh_cluster_summary(cluster_id)
        except (AiUnavailableError, AiBudgetExceededError):
            console.print(f"[yellow]summary of group {cluster_id} left stale[/]")


async def run(*, apply: bool, include: set[str]) -> int:
    setup_logging()
    try:
        await init_db()
        async with session_scope() as session:
            if apply:
                counts, kept = await purge(session, include)
            else:
                counts, kept = await plan(session, include), []
                await session.rollback()
        show(counts, applied=apply)
        if kept:
            await refresh(kept)
            console.print(f"{len(kept)} groups recounted and summarised")
        if not apply:
            console.print("add --apply to delete")
    finally:
        await container.close()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Delete user rows that are not registered as demo data"
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--include", action="append", choices=NAMES, default=[])
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(apply=args.apply, include=set(args.include))))


if __name__ == "__main__":
    main()
