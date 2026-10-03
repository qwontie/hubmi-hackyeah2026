import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import ApiError, not_found
from api.limits import client_ip, persistent_rate_limit
from api.routers.api.public.common import translate
from api.security import AdminPerson
from services.bus import bus
from services.dialogue.service import spawn
from services.mail import Mailer
from services.modules import Page
from services.needs import TextRejectedError
from services.tester import demand, emails, volunteers
from services.tester.intake import checked_text, honeypot_check
from services.tester.schemas import (
    MESSAGE_MAX,
    PROPOSAL_MAX,
    PROPOSAL_MIN,
    REASON_MAX,
    REPORT_TEXT_MAX,
    AcceptIn,
    AdaptationVolunteers,
    AdminVolunteer,
    AdminVolunteerDetail,
    DemandByPowiat,
    DemandCount,
    DemandCreated,
    DemandEntry,
    DemandIn,
    InnovationReports,
    MessageIn,
    RejectIn,
    ReportIn,
    VolunteerCounts,
    VolunteerCreated,
    VolunteerIn,
    VolunteerMessageOut,
    VolunteerView,
)
from services.tester.volunteers import Action, InvalidTransitionError
from utils.db.models import Innovation
from utils.db.models.test_signup import SignupStatus, TesterRole, TestSignup
from utils.db.models.volunteer import VolunteerMessageKind
from utils.logging import logger

from .common import (
    PageNumber,
    PerPage,
    PowiatFilter,
    ReadLimited,
    SearchFilter,
    SlugFilter,
    consented_email,
    innovation_or_404,
    optional_email,
    optional_text,
    powiat_name,
)

public = APIRouter(route_class=DishkaRoute, tags=["volunteers"])
admin = APIRouter(route_class=DishkaRoute, tags=["volunteers"])

apply_limit = persistent_rate_limit("volunteer_apply", per_minute=5, per_day=20)
report_limit = persistent_rate_limit("volunteer_report", per_minute=10, per_day=60)
demand_limit = persistent_rate_limit("demand", per_minute=10, per_day=50)

ACTIVITY_MIN = 10
ANSWER_MIN = 2
MESSAGE_MIN = 2
REASON_MIN = 3
VOLUNTEER_MISSING = "Nie znaleziono tego zgłoszenia."
REPORT_LOCKED = (
    "Raportu nie można już zmienić. W razie pytań odpowiedz na e-mail od ROPS."
)
TRANSITION_MESSAGES = {
    Action.ACCEPT: "To zgłoszenie zostało już rozpatrzone.",
    Action.REJECT: "To zgłoszenie zostało już rozpatrzone.",
    Action.CLOSE: "Zamknąć można tylko przyjęte zgłoszenie.",
}

VolunteerToken = Annotated[
    str | None, Header(alias="X-Volunteer-Token", max_length=200)
]


def text_or_422(
    field: str, value: str, *, minimum: int, maximum: int, words: int = 2
) -> str:
    try:
        return checked_text(field, value, minimum=minimum, maximum=maximum, words=words)
    except TextRejectedError as e:
        raise translate(e) from e


def invalid_transition(action: Action) -> ApiError:
    return ApiError(
        status.HTTP_409_CONFLICT, "invalid_transition", TRANSITION_MESSAGES[action]
    )


async def send_confirmation(mailer: Mailer, signup: TestSignup, title: str) -> None:
    try:
        await mailer.send(
            emails.confirmation(
                to=signup.contact_email,
                title=title,
                proposal=signup.note,
                key=f"volunteer-confirmation-{signup.id}",
            )
        )
    except Exception:
        logger.exception("volunteer confirmation failed for %s", signup.id)


@public.post(
    "/innovations/{slug}/volunteers",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(apply_limit)],
)
async def apply(
    slug: str,
    body: VolunteerIn,
    response: Response,
    session: FromDishka[AsyncSession],
    mailer: FromDishka[Mailer],
) -> VolunteerCreated:
    try:
        honeypot_check(body.website)
    except TextRejectedError as e:
        raise translate(e) from e
    innovation = await innovation_or_404(session, slug)
    email = consented_email(body.email, body.contact_consent)
    powiat_name("powiat", body.powiat)
    proposal = text_or_422(
        "proposal", body.proposal, minimum=PROPOSAL_MIN, maximum=PROPOSAL_MAX
    )
    signup, duplicate = await volunteers.apply(
        session,
        innovation_id=innovation.id,
        who=body.who,
        organization=optional_text("organization", body.organization, line=True),
        powiat=body.powiat,
        email=email,
        proposal=proposal,
    )
    if duplicate:
        response.status_code = status.HTTP_200_OK
    else:
        bus.publish(
            "volunteer.created", volunteers.admin_volunteer(signup, innovation, None)
        )
        spawn(send_confirmation(mailer, signup, innovation.title))
    return VolunteerCreated(id=signup.id, duplicate=duplicate)


async def opened(
    session: AsyncSession, signup_id: uuid.UUID, token: str | None
) -> tuple[TestSignup, VolunteerView]:
    row = None
    if volunteers.token_opens(signup_id, token):
        row = await volunteers.load(session, signup_id)
    if row is None:
        raise not_found(VOLUNTEER_MISSING)
    return row[0], volunteers.volunteer_view(*row)


@public.get("/volunteers/{signup_id}")
async def volunteer(
    signup_id: uuid.UUID,
    session: FromDishka[AsyncSession],
    _: ReadLimited,
    token: VolunteerToken = None,
) -> VolunteerView:
    return (await opened(session, signup_id, token))[1]


@public.put("/volunteers/{signup_id}/report", dependencies=[Depends(report_limit)])
async def put_report(
    signup_id: uuid.UUID,
    body: ReportIn,
    session: FromDishka[AsyncSession],
    token: VolunteerToken = None,
) -> VolunteerView:
    signup, view = await opened(session, signup_id, token)
    if not view.editable:
        raise ApiError(status.HTTP_409_CONFLICT, "report_locked", REPORT_LOCKED)
    activity = text_or_422(
        "activity", body.activity, minimum=ACTIVITY_MIN, maximum=REPORT_TEXT_MAX
    )
    worked = text_or_422(
        "worked", body.worked, minimum=ANSWER_MIN, maximum=REPORT_TEXT_MAX, words=1
    )
    not_worked = text_or_422(
        "not_worked",
        body.not_worked,
        minimum=ANSWER_MIN,
        maximum=REPORT_TEXT_MAX,
        words=1,
    )
    try:
        await volunteers.save_report(
            session,
            signup,
            activity=activity,
            participants=body.participants,
            worked=worked,
            not_worked=not_worked,
            recommend=body.recommend,
        )
    except InvalidTransitionError as e:
        raise ApiError(status.HTTP_409_CONFLICT, "report_locked", REPORT_LOCKED) from e
    row = await volunteers.load(session, signup_id)
    if row is None:
        raise not_found(VOLUNTEER_MISSING)
    bus.publish("volunteer.reported", volunteers.admin_volunteer(*row))
    return volunteers.volunteer_view(*row)


@public.post(
    "/innovations/{slug}/demand",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(demand_limit)],
)
async def post_demand(
    slug: str,
    body: DemandIn,
    request: Request,
    response: Response,
    session: FromDishka[AsyncSession],
) -> DemandCreated:
    try:
        honeypot_check(body.website)
    except TextRejectedError as e:
        raise translate(e) from e
    innovation = await innovation_or_404(session, slug)
    powiat_name("powiat", body.powiat)
    email = optional_email(body.email, body.contact_consent)
    created = await demand.add(
        session,
        innovation_id=innovation.id,
        powiat=body.powiat,
        email=email,
        ip=client_ip(request),
    )
    if created is None:
        response.status_code = status.HTTP_200_OK
    else:
        bus.publish("demand.created", demand.entry(created, innovation))
    return DemandCreated(
        count=await demand.count(session, innovation.id), duplicate=created is None
    )


@public.get("/innovations/{slug}/demand")
async def get_demand(
    slug: str, session: FromDishka[AsyncSession], _: ReadLimited
) -> DemandCount:
    innovation = await innovation_or_404(session, slug)
    return DemandCount(count=await demand.count(session, innovation.id))


@admin.get("/volunteers")
async def list_volunteers(  # noqa: PLR0913
    *,
    _admin: AdminPerson,
    session: FromDishka[AsyncSession],
    status_: Annotated[SignupStatus | None, Query(alias="status")] = None,
    who: TesterRole | None = None,
    powiat: PowiatFilter = None,
    innovation: SlugFilter = None,
    q: SearchFilter = None,
    page: PageNumber = 1,
    per_page: PerPage = 20,
) -> Page[AdminVolunteer]:
    return await volunteers.list_volunteers(
        session,
        status=status_,
        who=who,
        powiat=powiat,
        innovation=innovation,
        q=q,
        page=page,
        per_page=per_page,
    )


@admin.get("/volunteers/counts")
async def volunteer_counts(
    _admin: AdminPerson, session: FromDishka[AsyncSession]
) -> VolunteerCounts:
    return await volunteers.counts(session)


@admin.get("/volunteers/reports")
async def innovation_reports(
    innovation: Annotated[str, Query(max_length=200, pattern=r"^[^\x00]+$")],
    _admin: AdminPerson,
    session: FromDishka[AsyncSession],
) -> InnovationReports:
    found = await innovation_or_404(session, innovation)
    return await volunteers.innovation_reports(session, found)


@admin.get("/volunteers/for-adaptation/{adaptation_id}")
async def for_adaptation(
    adaptation_id: uuid.UUID, _admin: AdminPerson, session: FromDishka[AsyncSession]
) -> AdaptationVolunteers:
    result = await volunteers.near_adaptation(session, adaptation_id)
    if result is None:
        raise not_found()
    return result


async def detail_or_404(
    session: AsyncSession, signup_id: uuid.UUID
) -> AdminVolunteerDetail:
    result = await volunteers.detail(session, signup_id)
    if result is None:
        raise not_found(VOLUNTEER_MISSING)
    return result


async def signup_or_404(session: AsyncSession, signup_id: uuid.UUID) -> TestSignup:
    signup = await session.get(TestSignup, signup_id)
    if signup is None:
        raise not_found(VOLUNTEER_MISSING)
    return signup


async def innovation_title(session: AsyncSession, signup: TestSignup) -> str:
    innovation = await session.get(Innovation, signup.innovation_id)
    return innovation.title if innovation else ""


async def announce(session: AsyncSession, signup_id: uuid.UUID) -> None:
    row = await volunteers.load(session, signup_id)
    if row is not None:
        bus.publish("volunteer.updated", volunteers.admin_volunteer(*row))


@admin.get("/volunteers/{signup_id}")
async def volunteer_detail(
    signup_id: uuid.UUID, _admin: AdminPerson, session: FromDishka[AsyncSession]
) -> AdminVolunteerDetail:
    return await detail_or_404(session, signup_id)


@admin.post("/volunteers/{signup_id}/messages", status_code=status.HTTP_201_CREATED)
async def write(
    signup_id: uuid.UUID,
    body: MessageIn,
    admin_: AdminPerson,
    session: FromDishka[AsyncSession],
    mailer: FromDishka[Mailer],
) -> VolunteerMessageOut:
    signup = await signup_or_404(session, signup_id)
    text = text_or_422(
        "body", body.body, minimum=MESSAGE_MIN, maximum=MESSAGE_MAX, words=1
    )
    message = await volunteers.send(
        session,
        signup=signup,
        kind=VolunteerMessageKind.MESSAGE,
        body=text,
        admin=admin_,
        mailer=mailer,
    )
    await announce(session, signup_id)
    return volunteers.message_out(message, admin_.login)


async def decide(  # noqa: PLR0913
    session: AsyncSession,
    signup: TestSignup,
    *,
    action: Action,
    body: str,
    reason: str | None,
    admin_: AdminPerson,
    mailer: Mailer,
) -> AdminVolunteerDetail:
    try:
        await volunteers.decide(
            session,
            signup,
            action=action,
            body=body,
            reason=reason,
            admin=admin_,
            mailer=mailer,
        )
    except InvalidTransitionError as e:
        raise invalid_transition(action) from e
    await announce(session, signup.id)
    return await detail_or_404(session, signup.id)


@admin.post("/volunteers/{signup_id}/accept")
async def accept(
    signup_id: uuid.UUID,
    body: AcceptIn,
    admin_: AdminPerson,
    session: FromDishka[AsyncSession],
    mailer: FromDishka[Mailer],
) -> AdminVolunteerDetail:
    signup = await signup_or_404(session, signup_id)
    if signup.status != SignupStatus.NEW:
        raise invalid_transition(Action.ACCEPT)
    text = (
        emails.accept_draft(await innovation_title(session, signup))
        if body.body is None
        else text_or_422(
            "body", body.body, minimum=MESSAGE_MIN, maximum=MESSAGE_MAX, words=1
        )
    )
    return await decide(
        session,
        signup,
        action=Action.ACCEPT,
        body=text,
        reason=None,
        admin_=admin_,
        mailer=mailer,
    )


@admin.post("/volunteers/{signup_id}/reject")
async def reject(
    signup_id: uuid.UUID,
    body: RejectIn,
    admin_: AdminPerson,
    session: FromDishka[AsyncSession],
    mailer: FromDishka[Mailer],
) -> AdminVolunteerDetail:
    signup = await signup_or_404(session, signup_id)
    if signup.status != SignupStatus.NEW:
        raise invalid_transition(Action.REJECT)
    reason = text_or_422(
        "reason", body.reason, minimum=REASON_MIN, maximum=REASON_MAX, words=1
    )
    template = (
        emails.reject_draft(await innovation_title(session, signup))
        if body.body is None
        else text_or_422(
            "body", body.body, minimum=MESSAGE_MIN, maximum=MESSAGE_MAX, words=1
        )
    )
    return await decide(
        session,
        signup,
        action=Action.REJECT,
        body=template.replace(emails.REASON_SLOT, reason),
        reason=reason,
        admin_=admin_,
        mailer=mailer,
    )


@admin.post("/volunteers/{signup_id}/close")
async def close(
    signup_id: uuid.UUID, admin_: AdminPerson, session: FromDishka[AsyncSession]
) -> AdminVolunteerDetail:
    signup = await signup_or_404(session, signup_id)
    try:
        await volunteers.close(session, signup, admin_)
    except InvalidTransitionError as e:
        raise invalid_transition(Action.CLOSE) from e
    await announce(session, signup_id)
    return await detail_or_404(session, signup_id)


@admin.get("/demand")
async def demand_by_powiat(
    *,
    _admin: AdminPerson,
    session: FromDishka[AsyncSession],
    innovation: SlugFilter = None,
    powiat: PowiatFilter = None,
    page: PageNumber = 1,
    per_page: PerPage = 20,
) -> Page[DemandByPowiat]:
    return await demand.by_powiat(
        session, innovation=innovation, powiat=powiat, page=page, per_page=per_page
    )


@admin.get("/demand/entries")
async def demand_entries(  # noqa: PLR0913
    *,
    _admin: AdminPerson,
    session: FromDishka[AsyncSession],
    innovation: SlugFilter = None,
    powiat: PowiatFilter = None,
    with_email: bool | None = None,
    page: PageNumber = 1,
    per_page: PerPage = 20,
) -> Page[DemandEntry]:
    return await demand.entries(
        session,
        innovation=innovation,
        powiat=powiat,
        with_email=with_email,
        page=page,
        per_page=per_page,
    )
