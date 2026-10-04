import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import col, delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.routers.api.admin import contacts as routes
from services.dialogue import erase
from services.dialogue.schemas import ContactProfileRequest
from utils.db import session_scope
from utils.db.models import (
    AdminAction,
    AdminRole,
    AdminUser,
    Assignment,
    Category,
    ExpertNote,
    GrantApplication,
    GrantCall,
    GrantCallStatus,
    GrantNoticeDelivery,
    GrantSubscriber,
    Idea,
    IdeaStage,
    Innovation,
    InnovationStatus,
    Need,
    NeedOrigin,
    TesterRole,
    TestSignup,
)
from utils.db.models.demand import InnovationDemand
from utils.db.models.volunteer import (
    Recommendation,
    VolunteerMessage,
    VolunteerMessageKind,
    VolunteerReport,
)

NEED_TEXT = "Brakuje transportu do lekarza dla seniorów z gminy"


@dataclass
class Person:
    email: str
    need: Need
    idea: Idea
    application: GrantApplication
    demand: InnovationDemand
    signup: TestSignup
    assignment: Assignment
    subscriber: GrantSubscriber


@dataclass
class World:
    tag: str
    admin: AdminUser
    category: Category
    innovation: Innovation
    call: GrantCall
    target: Person
    other: Person


def person(world: tuple[AdminUser, Innovation, GrantCall], email: str) -> Person:
    admin, innovation, call = world
    now = datetime.now(UTC)
    need = Need(
        text=f"{NEED_TEXT} {email}",
        origin=NeedOrigin.FORM,
        edit_token_hash=uuid.uuid4().hex,
        contact_email=email,
        contact_consent=True,
        consent_at=now,
    )
    idea = Idea(
        title="Sąsiedzki bus",
        essence="Wolontariusze wożą seniorów do przychodni.",
        for_whom="Seniorzy",
        stage=IdeaStage.IDEA,
        canvas={},
        edit_token_hash=uuid.uuid4().hex,
        contact_email=email,
        contact_consent=True,
        consent_at=now,
    )
    return Person(
        email=email,
        need=need,
        idea=idea,
        application=GrantApplication(
            call_id=call.id, idea_id=idea.id, contact_email=email, contact_consent=True
        ),
        demand=InnovationDemand(
            innovation_id=innovation.id,
            powiat="wielicki",
            contact_email=email,
            consent_at=now,
            client_key=uuid.uuid4().hex,
            day=now.date(),
        ),
        signup=TestSignup(
            innovation_id=innovation.id,
            who=TesterRole.RESIDENT,
            contact_email=email,
            consent_at=now,
            note="Mogę testować w soboty.",
        ),
        assignment=Assignment(
            expert_email=email,
            expert_name="Ekspert Testowy",
            need_id=need.id,
            assigned_by=admin.login,
        ),
        subscriber=GrantSubscriber(email=email, consent_at=now),
    )


@pytest.fixture
async def world(database: None) -> AsyncGenerator[World]:
    del database
    tag = uuid.uuid4().hex[:10]
    now = datetime.now(UTC)
    admin = AdminUser(
        login=f"test-admin-{tag}",
        password_hash="x",  # noqa: S106
        role=AdminRole.ADMIN,
    )
    category = Category(
        slug=f"test-cat-{tag}", name="Test", source_url="https://rops.krakow.pl"
    )
    innovation = Innovation(
        slug=f"test-inno-{tag}",
        category_slug=category.slug,
        title="Rozwiązanie testowe",
        status=InnovationStatus.PUBLISHED,
    )
    call = GrantCall(
        title=f"Nabór testowy {tag}",
        description="Opis naboru testowego.",
        opens_at=now - timedelta(days=1),
        closes_at=now + timedelta(days=7),
        status=GrantCallStatus.PUBLISHED,
    )
    base = (admin, innovation, call)
    target = person(base, f"Anna.{tag}@Example.org")
    other = person(base, f"jan.{tag}@example.org")
    async with session_scope() as session:
        session.add_all([admin, category])
        await session.flush()
        session.add_all([innovation, call])
        await session.flush()
        for one in (target, other):
            session.add_all([one.need, one.idea, one.subscriber])
            await session.flush()
            session.add_all([one.application, one.demand, one.signup, one.assignment])
            await session.flush()
            session.add_all(
                [
                    VolunteerMessage(
                        signup_id=one.signup.id,
                        kind=VolunteerMessageKind.ACCEPT,
                        body="Dzień dobry, zapraszamy do testów.",
                    ),
                    VolunteerReport(
                        signup_id=one.signup.id,
                        activity="Test w świetlicy",
                        participants=5,
                        worked="Prosta obsługa",
                        not_worked="Brak instrukcji",
                        recommend=Recommendation.YES,
                    ),
                    ExpertNote(assignment_id=one.assignment.id, body="Uwaga eksperta"),
                    GrantNoticeDelivery(
                        call_id=call.id,
                        subscriber_id=one.subscriber.id,
                        notice_key="opened",
                        opened=True,
                    ),
                ]
            )
        await session.commit()
    yield World(tag, admin, category, innovation, call, target, other)
    async with session_scope() as session:
        emails = [target.email, other.email]
        await session.exec(
            delete(GrantSubscriber).where(col(GrantSubscriber.email).in_(emails))
        )
        await session.exec(
            delete(GrantApplication).where(col(GrantApplication.call_id) == call.id)
        )
        await session.exec(delete(GrantCall).where(col(GrantCall.id) == call.id))
        ideas = [target.idea.id, other.idea.id]
        await session.exec(delete(Idea).where(col(Idea.id).in_(ideas)))
        needs = [target.need.id, other.need.id]
        await session.exec(delete(Need).where(col(Need.id).in_(needs)))
        await session.exec(
            delete(Innovation).where(col(Innovation.id) == innovation.id)
        )
        await session.exec(delete(Category).where(col(Category.slug) == category.slug))
        await session.exec(
            delete(AdminAction).where(col(AdminAction.admin_id) == admin.id)
        )
        await session.exec(delete(AdminUser).where(col(AdminUser.id) == admin.id))
        await session.commit()


async def assert_children(session: AsyncSession, one: Person, *, present: bool) -> None:
    owned = (
        (VolunteerMessage, VolunteerMessage.signup_id, one.signup.id),
        (VolunteerReport, VolunteerReport.signup_id, one.signup.id),
        (ExpertNote, ExpertNote.assignment_id, one.assignment.id),
        (GrantNoticeDelivery, GrantNoticeDelivery.subscriber_id, one.subscriber.id),
    )
    for model, column, owner in owned:
        rows = (await session.exec(select(model).where(col(column) == owner))).all()
        assert bool(rows) is present


async def call_erase(world: World, email: str) -> erase.EraseResult:
    async with session_scope() as session:
        return await routes.erase_contact(
            ContactProfileRequest(email=email), world.admin, session
        )


async def assert_erased(session: AsyncSession, target: Person) -> None:
    need = await session.get(Need, target.need.id)
    assert need is not None
    assert need.contact_email is None
    assert not need.contact_consent
    assert need.consent_at is None
    assert need.text.startswith(NEED_TEXT)
    assert need.edit_token_hash == target.need.edit_token_hash
    idea = await session.get(Idea, target.idea.id)
    assert idea is not None
    assert idea.contact_email is None
    assert not idea.contact_consent
    assert idea.edit_token_hash == target.idea.edit_token_hash
    application = await session.get(GrantApplication, target.application.id)
    assert application is not None
    assert application.contact_email is None
    assert not application.contact_consent
    demand = await session.get(InnovationDemand, target.demand.id)
    assert demand is not None
    assert demand.contact_email is None
    assert demand.consent_at is None
    await assert_children(session, target, present=False)
    assert await session.get(TestSignup, target.signup.id) is None
    assert await session.get(Assignment, target.assignment.id) is None
    assert await session.get(GrantSubscriber, target.subscriber.id) is None


async def assert_kept(session: AsyncSession, other: Person) -> None:
    kept_need = await session.get(Need, other.need.id)
    assert kept_need is not None
    assert kept_need.contact_email == other.email
    assert kept_need.contact_consent
    kept_idea = await session.get(Idea, other.idea.id)
    assert kept_idea is not None
    assert kept_idea.contact_email == other.email
    kept_application = await session.get(GrantApplication, other.application.id)
    assert kept_application is not None
    assert kept_application.contact_email == other.email
    kept_demand = await session.get(InnovationDemand, other.demand.id)
    assert kept_demand is not None
    assert kept_demand.contact_email == other.email
    assert await session.get(TestSignup, other.signup.id) is not None
    assert await session.get(Assignment, other.assignment.id) is not None
    assert await session.get(GrantSubscriber, other.subscriber.id) is not None
    await assert_children(session, other, present=True)


async def test_erase_clears_every_place_and_keeps_others(world: World) -> None:
    target, other = world.target, world.other
    result = await call_erase(world, f"  ANNA.{world.tag}@example.ORG ")
    assert result.erased == {
        "need": 1,
        "idea": 1,
        "grant_application": 1,
        "innovation_demand": 1,
        "test_signup": 1,
        "volunteer_message": 1,
        "volunteer_report": 1,
        "assignment": 1,
        "expert_note": 1,
        "grant_subscriber": 1,
        "grant_notice_delivery": 1,
    }
    assert result.total == 11
    async with session_scope() as session:
        await assert_erased(session, target)
        await assert_kept(session, other)

    again = await call_erase(world, target.email)
    assert again.total == 0
    assert set(again.erased.values()) == {0}

    async with session_scope() as session:
        actions = (
            await session.exec(
                select(AdminAction)
                .where(col(AdminAction.admin_id) == world.admin.id)
                .order_by(col(AdminAction.created_at))
            )
        ).all()
    assert [action.action for action in actions] == [erase.ACTION, erase.ACTION]
    first = actions[0]
    assert first.details["total"] == 11
    assert first.details["erased"] == result.erased
    assert first.details["address_hash"] == erase.address_hash(target.email.lower())
    stored = f"{first.target_id} {first.details}".lower()
    assert target.email.lower() not in stored
    assert world.tag not in stored


async def test_unknown_address_returns_zero(world: World) -> None:
    result = await call_erase(world, f"nikt.{world.tag}@example.org")
    assert result.total == 0
    async with session_scope() as session:
        need = await session.get(Need, world.target.need.id)
        assert need is not None
        assert need.contact_email == world.target.email
