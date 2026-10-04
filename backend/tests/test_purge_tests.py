# ruff: noqa: S608
import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from sqlalchemy import TextClause, text
from sqlmodel.ext.asyncio.session import AsyncSession

from scripts.demo import purge_tests, registry
from tests.conftest import one_hot
from utils.db import session_scope
from utils.db.models.need import Need, NeedCluster, NeedOrigin

CLEAN = ("need", "idea", "demo_record", "test_signup", "grant_call", "innovation")


async def insert(session: AsyncSession, table: str, **values: Any) -> uuid.UUID:
    values = {"id": uuid.uuid4(), **values}
    names = ", ".join(values)
    params = ", ".join(
        value.text if isinstance(value, TextClause) else f":{name}"
        for name, value in values.items()
    )
    bound = {k: v for k, v in values.items() if not isinstance(v, TextClause)}
    found = await session.scalar(
        text(f"INSERT INTO {table} ({names}) VALUES ({params}) RETURNING id"), bound
    )
    assert found is not None
    return found


async def demo(session: AsyncSession, kind: str, row_id: uuid.UUID) -> None:
    await insert(session, "demo_record", kind=kind, key=str(row_id), row_id=row_id)


async def need(
    session: AsyncSession, body: str, cluster: NeedCluster, email: str | None = None
) -> uuid.UUID:
    row = Need(
        text=body,
        title=body,
        origin=NeedOrigin.FORM,
        edit_token_hash=uuid.uuid4().hex,
        cluster_id=cluster.id,
        embedding=one_hot(body),
        contact_email=email,
    )
    session.add(row)
    await session.flush()
    return row.id


async def count(session: AsyncSession, table: str, where: str = "true") -> int:
    return int(
        await session.scalar(text(f"SELECT count(*) FROM {table} WHERE {where}")) or 0
    )


async def seed_items(
    session: AsyncSession, ids: dict[str, uuid.UUID], inno: uuid.UUID, call: uuid.UUID
) -> None:
    for key in ("need", "junk_need"):
        await insert(
            session,
            "match_result",
            need_id=ids[key],
            innovation_id=inno,
            rank=1,
            score=0.5,
            reason="powód",
        )
    for key, voter in (("feedback", "v1"), ("junk_feedback", "v2")):
        ids[key] = await insert(
            session, "feedback", innovation_id=inno, kind="fits", voter_hash=voter
        )
    await demo(session, registry.FEEDBACK, ids["feedback"])
    for key in ("idea", "junk_idea"):
        ids[key] = await insert(
            session,
            "idea",
            title=f"{key} tytuł",
            essence="Opis pomysłu",
            for_whom="Seniorzy",
            stage="idea",
            canvas=json.dumps({}),
            edit_token_hash=uuid.uuid4().hex,
            problem_id=ids["kept_group" if key == "idea" else "junk_group"],
        )
        await purge_tests.sql(
            session,
            text(
                "INSERT INTO idea_visualisation "
                "(idea_id, version, image, mime_type, prompt, alt, model) "
                "VALUES (:idea, 1, '\\x00', 'image/png', 'p', 'alt', 'm')"
            ).bindparams(idea=ids[key]),
        )
    await demo(session, registry.IDEA, ids["idea"])
    for key, idea in (
        ("held_application", ids["idea"]),
        ("junk_application", ids["junk_idea"]),
        ("loose_application", None),
    ):
        ids[key] = await insert(
            session,
            "grant_application",
            call_id=call,
            idea_id=idea,
            contact_email="team@example.com",
        )
    for key in ("signup", "junk_signup"):
        ids[key] = await insert(
            session,
            "test_signup",
            innovation_id=inno,
            who="resident",
            contact_email=f"{key}@example.com",
            consent_at=text("now()"),
        )
        await insert(
            session,
            "volunteer_report",
            signup_id=ids[key],
            activity="test",
            participants=1,
            worked="x",
            not_worked="y",
            recommend="yes",
        )
        ids[f"{key}_message"] = await insert(
            session,
            "volunteer_message",
            signup_id=ids[key],
            kind="message",
            body="hej",
            delivery_status="sent",
        )
    await demo(session, registry.SIGNUP, ids["signup"])
    for key in ("demand", "junk_demand"):
        ids[key] = await insert(
            session,
            "innovation_demand",
            innovation_id=inno,
            powiat="krakowski",
            client_key=key,
            day=text("current_date"),
        )
    await demo(session, registry.DEMAND, ids["demand"])
    for key in ("adaptation", "junk_adaptation"):
        ids[key] = await insert(
            session,
            "adaptation",
            innovation_id=inno,
            institution_type="ngo",
            place="Kraków",
            context="kontekst",
            plan=json.dumps({}),
            model="m",
        )
    await demo(session, registry.ADAPTATION, ids["adaptation"])
    for key, email in (("assignment", "e1@x.pl"), ("junk_assignment", "e2@x.pl")):
        ids[key] = await insert(
            session,
            "assignment",
            need_id=ids["need"],
            expert_email=email,
            assigned_by="test",
        )
    await insert(session, "expert_note", assignment_id=ids["junk_assignment"], body="n")
    await demo(session, registry.ASSIGNMENT, ids["assignment"])
    subscriber = await insert(
        session, "grant_subscriber", email="me@example.com", consent_at=text("now()")
    )
    await insert(
        session,
        "grant_notice_delivery",
        call_id=call,
        subscriber_id=subscriber,
        notice_key="open",
        opened=True,
    )
    await insert(session, "search_log", outcome="ok", degraded=False)
    await purge_tests.sql(
        session,
        text(
            "INSERT INTO rate_counter (key_hash, window_start, hits) "
            "VALUES ('k', now(), 1)"
        ),
    )


@pytest.fixture
async def seeded(database: None) -> AsyncGenerator[dict[str, uuid.UUID]]:
    del database
    async with session_scope() as session:
        for table in CLEAN:
            if await count(session, table):
                pytest.skip("purge test needs an empty database, it deletes user rows")
        tag = uuid.uuid4().hex[:8]
        ids: dict[str, uuid.UUID] = {}
        await purge_tests.sql(
            session,
            text(
                "INSERT INTO category (id, slug, name, source_url) "
                "VALUES (:id, :slug, 'Test', 'https://rops.krakow.pl')"
            ).bindparams(id=uuid.uuid4(), slug=f"purge-{tag}"),
        )
        inno = await insert(
            session,
            "innovation",
            slug=f"purge-{tag}",
            category_slug=f"purge-{tag}",
            title="Rozwiązanie testowe",
            status="published",
        )
        call = await insert(
            session,
            "grant_call",
            title="Nabór",
            description="Opis",
            opens_at=text("now()"),
            closes_at=text("now() + interval '7 days'"),
            status="published",
        )
        kept_group = NeedCluster(title="Samotność seniorów", size=2)
        junk_group = NeedCluster(title="mam biegunke", size=1)
        session.add_all([kept_group, junk_group])
        await session.flush()
        ids["kept_group"], ids["junk_group"] = kept_group.id, junk_group.id
        await demo(session, registry.CLUSTER, kept_group.id)
        ids["need"] = await need(session, "Seniorzy są samotni w zimie", kept_group)
        ids["junk_need"] = await need(session, "mam biegunke", kept_group, "a@b.pl")
        ids["junk_need_2"] = await need(session, "asdasd biegunka", junk_group)
        await demo(session, registry.NEED, ids["need"])
        for key, owner in (("message", "need"), ("junk_message", "need")):
            ids[key] = await insert(
                session,
                "message",
                need_id=ids[owner],
                direction="to_author",
                body=f"{key} body",
            )
        await insert(
            session,
            "message",
            need_id=ids["junk_need"],
            direction="from_author",
            body="test",
        )
        await demo(session, registry.MESSAGE, ids["message"])
        await seed_items(session, ids, inno, call)
        await session.commit()
    yield ids
    async with session_scope() as session:
        await purge_tests.sql(session, text("DELETE FROM demo_record"))
        await purge_tests.purge(session, set(purge_tests.NAMES))
        for table in ("grant_call", "innovation", "category"):
            await purge_tests.sql(session, text(f"DELETE FROM {table}"))
        await session.commit()


def by_table(counts: list[purge_tests.Count]) -> dict[str, purge_tests.Count]:
    return {c.table: c for c in counts}


async def test_dry_run_changes_nothing(seeded: dict[str, uuid.UUID]) -> None:
    del seeded
    async with session_scope() as session:
        before = await count(session, "need")
        counts = by_table(await purge_tests.plan(session, set()))
        await session.rollback()
        assert await count(session, "need") == before == 3
    assert counts["need"].delete == 2
    assert counts["need"].demo == 1
    assert counts["need_cluster"].delete == 1
    assert counts["grant_application"].held == 1
    assert counts["grant_application"].delete == 2
    assert counts["search_log"].delete == 1
    assert all(
        "@" not in value or "***@" in value
        for c in counts.values()
        for _, value in c.samples
    )


async def test_purge_keeps_demo_and_fixes_groups(seeded: dict[str, uuid.UUID]) -> None:
    ids = seeded
    async with session_scope() as session:
        counts, recounted = await purge_tests.purge(session, set())
    deleted = {c.table: c.deleted for c in counts}
    assert deleted["need"] == 2
    assert deleted["need_cluster"] == 1
    assert recounted == [ids["kept_group"]]
    async with session_scope() as session:
        for key, table in (
            ("need", "need"),
            ("message", "message"),
            ("feedback", "feedback"),
            ("idea", "idea"),
            ("held_application", "grant_application"),
            ("signup", "test_signup"),
            ("signup_message", "volunteer_message"),
            ("demand", "innovation_demand"),
            ("adaptation", "adaptation"),
            ("assignment", "assignment"),
        ):
            assert await count(session, table, f"id = '{ids[key]}'") == 1, key
        for key, table in (
            ("junk_need", "need"),
            ("junk_need_2", "need"),
            ("junk_message", "message"),
            ("junk_feedback", "feedback"),
            ("junk_idea", "idea"),
            ("junk_application", "grant_application"),
            ("loose_application", "grant_application"),
            ("junk_signup", "test_signup"),
            ("junk_signup_message", "volunteer_message"),
            ("junk_demand", "innovation_demand"),
            ("junk_adaptation", "adaptation"),
            ("junk_assignment", "assignment"),
            ("junk_group", "need_cluster"),
        ):
            assert not await count(session, table, f"id = '{ids[key]}'"), key
        for table in ("grant_subscriber", "search_log", "rate_counter", "expert_note"):
            assert not await count(session, table), table
        assert await count(session, "message") == 1
        assert await count(session, "match_result") == 1
        assert await count(session, "volunteer_report") == 1
        assert await count(session, "idea_visualisation") == 1
        group = await session.get(NeedCluster, ids["kept_group"])
        assert group is not None
        assert group.size == 1
        assert group.centroid is not None
        assert list(group.centroid) == one_hot("Seniorzy są samotni w zimie")
        assert not await count(
            session,
            "need_cluster",
            "size <> (SELECT count(*) FROM need WHERE cluster_id = need_cluster.id)",
        )
        assert await count(session, "demo_record") == 9
        assert await count(session, "innovation") == 1
        assert await count(session, "grant_call") == 1
    async with session_scope() as session:
        again, recounted = await purge_tests.purge(session, set())
    assert not recounted
    assert all(not c.deleted for c in again), [(c.table, c.deleted) for c in again]
    async with session_scope() as session:
        counts, _ = await purge_tests.purge(session, {"grant_application"})
    assert by_table(counts)["grant_application"].deleted == 1


async def test_unregistered_table_is_kept(seeded: dict[str, uuid.UUID]) -> None:
    async with session_scope() as session:
        await purge_tests.sql(
            session, text("DELETE FROM demo_record WHERE kind = 'adaptation'")
        )
        await session.commit()
        counts = by_table(await purge_tests.plan(session, set()))
        assert counts["adaptation"].delete == 0
        assert counts["adaptation"].held == 2
        assert "not in demo_record" in counts["adaptation"].note
        included = by_table(await purge_tests.plan(session, {"adaptation"}))
        assert included["adaptation"].delete == 2
        await session.rollback()
    assert seeded
