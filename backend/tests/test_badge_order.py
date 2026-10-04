import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest
from conftest import one_hot
from sqlmodel import col, delete

from api.routers.api.public import innovations as library
from api.routers.api.public import match as matching
from api.routers.api.public.schemas import MatchIn
from services.needs import SearchOutcome
from services.search import (
    Hit,
    Reasoned,
    Signals,
    badge_order,
    hybrid,
    innovation_signals,
)
from utils.db import session_scope
from utils.db.models import Category, Innovation, TestSignup
from utils.db.models.feedback import Feedback, FeedbackKind
from utils.db.models.innovation import InnovationStatus
from utils.db.models.test_signup import SignupStatus, TesterRole
from utils.db.models.volunteer import Recommendation, VolunteerReport


@dataclass(slots=True)
class Item:
    id: uuid.UUID
    name: str


def test_badge_order_checked_then_likes_then_previous_order() -> None:
    items = [Item(uuid.uuid4(), name) for name in "abcde"]
    signals = {
        items[1].id: Signals(up=5),
        items[2].id: Signals(up=1, reports=1),
        items[3].id: Signals(up=5),
        items[4].id: Signals(up=3, reports=2),
    }
    ordered = badge_order(items, signals, key=lambda item: item.id)
    assert [item.name for item in ordered] == ["e", "c", "b", "d", "a"]


@dataclass(slots=True)
class Shelf:
    category: str
    rows: dict[str, Innovation]


async def _report(
    session: Any, innovation: Innovation, recommend: Recommendation, n: int
) -> None:
    signup = TestSignup(
        innovation_id=innovation.id,
        who=TesterRole.RESIDENT,
        contact_email=f"wolontariusz{n}-{uuid.uuid4().hex[:6]}@example.org",
        consent_at=datetime.now(UTC),
        status=SignupStatus.REPORTED,
    )
    session.add(signup)
    await session.flush()
    session.add(
        VolunteerReport(
            signup_id=signup.id,
            activity="Spotkania w świetlicy",
            participants=8,
            worked="Rozmowy",
            not_worked="Godziny",
            recommend=recommend,
        )
    )


async def _likes(session: Any, innovation: Innovation, up: int, down: int) -> None:
    for kind, count in ((FeedbackKind.FITS, up), (FeedbackKind.DOES_NOT_FIT, down)):
        for _ in range(count):
            session.add(
                Feedback(
                    innovation_id=innovation.id, kind=kind, voter_hash=uuid.uuid4().hex
                )
            )


@pytest.fixture
async def shelf(database: None) -> AsyncGenerator[Shelf]:
    del database
    tag = uuid.uuid4().hex[:10]
    category = Category(
        slug=f"test-badge-{tag}", name="Test", source_url="https://rops.krakow.pl"
    )
    specs = {
        "plain": ("Alfa pomoc sąsiedzka", one_hot("alfa"), [], (1, 0)),
        "liked": ("Beta klub dla seniorów", one_hot("beta"), ["no"], (3, 0)),
        "checked": (
            "Gamma opieka wytchnieniowa",
            one_hot("osamotnienie"),
            ["yes"],
            (0, 0),
        ),
        "checked_liked": (
            "Delta świetlica",
            one_hot("delta"),
            ["after_changes", "yes", "no"],
            (2, 1),
        ),
    }
    async with session_scope() as session:
        session.add(category)
        await session.flush()
        rows: dict[str, Innovation] = {}
        for key, (title, vector, reports, (up, down)) in specs.items():
            row = Innovation(
                slug=f"test-badge-{key.replace('_', '-')}-{tag}",
                category_slug=category.slug,
                title=title,
                status=InnovationStatus.PUBLISHED,
                embedding=vector,
            )
            session.add(row)
            await session.flush()
            for n, recommend in enumerate(reports):
                await _report(session, row, Recommendation(recommend), n)
            await _likes(session, row, up, down)
            rows[key] = row
        await session.commit()
        for row in rows.values():
            await session.refresh(row)
        yield Shelf(category=category.slug, rows=rows)
        await session.exec(
            delete(Innovation).where(
                col(Innovation.id).in_([r.id for r in rows.values()])
            )
        )
        await session.exec(delete(Category).where(col(Category.slug) == category.slug))
        await session.commit()


async def test_signals_count_only_recommending_reports(shelf: Shelf) -> None:
    rows = shelf.rows
    async with session_scope() as session:
        signals = await innovation_signals(session, [r.id for r in rows.values()])
    assert signals[rows["plain"].id] == Signals(up=1, down=0, reports=0)
    assert signals[rows["liked"].id] == Signals(up=3, down=0, reports=0)
    assert signals[rows["checked"].id] == Signals(up=0, down=0, reports=1)
    assert signals[rows["checked_liked"].id] == Signals(up=2, down=1, reports=2)
    assert not signals[rows["liked"].id].checked
    assert signals[rows["checked"].id].checked


async def test_library_default_order_is_badge_then_likes(shelf: Shelf) -> None:
    async with session_scope() as session:
        page = await library.list_innovations(session, category=shelf.category)
    assert [i.slug for i in page.items] == [
        shelf.rows[key].slug for key in ("checked_liked", "checked", "liked", "plain")
    ]
    assert [(i.volunteer_checked, i.volunteer_reports) for i in page.items] == [
        (True, 2),
        (True, 1),
        (False, 0),
        (False, 0),
    ]
    assert page.items[0].votes.up == 2
    assert page.items[0].votes.down == 1
    assert page.total == 4


async def test_detail_carries_the_badge(shelf: Shelf) -> None:
    async with session_scope() as session:
        detail = await library.get_innovation(shelf.rows["checked"].slug, session)
        plain = await library.get_innovation(shelf.rows["plain"].slug, session)
    assert detail.volunteer_checked
    assert detail.volunteer_reports == 1
    assert not plain.volunteer_checked
    assert plain.volunteer_reports == 0


@pytest.fixture
def fake_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    async def embed(text: str, **_: Any) -> list[float]:
        return one_hot(text)

    monkeypatch.setattr(hybrid, "embed_query", embed)


@pytest.mark.usefixtures("fake_embedding")
async def test_library_search_drops_nonsense(shelf: Shelf) -> None:
    async with session_scope() as session:
        page = await library.list_innovations(
            session, category=shelf.category, q="asdfgh"
        )
    assert page.items == []
    assert page.total == 0


@pytest.mark.usefixtures("fake_embedding")
async def test_library_search_finds_other_word_forms(shelf: Shelf) -> None:
    async with session_scope() as session:
        forms = [
            await library.list_innovations(session, category=shelf.category, q=q)
            for q in ("seniorami", "senior", "świetlicy", "swietlice")
        ]
    assert [[i.slug for i in page.items] for page in forms] == [
        [shelf.rows["liked"].slug],
        [shelf.rows["liked"].slug],
        [shelf.rows["checked_liked"].slug],
        [shelf.rows["checked_liked"].slug],
    ]


@pytest.mark.usefixtures("fake_embedding")
async def test_library_search_keeps_close_meaning(shelf: Shelf) -> None:
    async with session_scope() as session:
        page = await library.list_innovations(
            session, category=shelf.category, q="osamotnienie"
        )
    assert [i.slug for i in page.items] == [shelf.rows["checked"].slug]


async def test_match_reorders_only_chosen_results(
    shelf: Shelf, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = shelf.rows
    chosen = [rows["plain"], rows["liked"], rows["checked"]]

    async def search_need(_: Any, __: str) -> SearchOutcome:
        return SearchOutcome(
            results=[
                Reasoned(
                    hit=Hit(
                        innovation=row, score=0.9 - n / 10, similarity=0.7, keyword=0
                    ),
                    reason=f"Powód {n}",
                )
                for n, row in enumerate(chosen)
            ],
            similar_count=0,
            cluster=None,
            degraded=False,
            reason=None,
        )

    async def no_log(_: SearchOutcome) -> None:
        return None

    monkeypatch.setattr(matching, "search_need", search_need)
    monkeypatch.setattr(matching, "log_search", no_log)
    async with session_scope() as session:
        out = await matching.match(MatchIn(text="potrzebuję pomocy dla mamy"), session)
    assert [r.innovation.slug for r in out.results] == [
        rows["checked"].slug,
        rows["liked"].slug,
        rows["plain"].slug,
    ]
    assert [r.reason for r in out.results] == ["Powód 2", "Powód 1", "Powód 0"]
    assert out.results[0].innovation.volunteer_checked
    assert rows["checked_liked"].slug not in [r.innovation.slug for r in out.results]
