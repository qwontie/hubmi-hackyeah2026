import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import conflict, invalid, not_found
from api.security import AdminPerson
from services.bus import bus
from services.dialogue.audit import record
from services.dialogue.service import spawn
from services.grants import TEMPLATES, applications, calls, notify, subscribers
from services.grants.schemas import (
    AdminApplication,
    AdminGrantCall,
    ApplicationPage,
    CallIn,
    CallPage,
    CallPatch,
    GrantTemplateOut,
    StatusIn,
)
from services.mail import Mailer
from utils.db.models import (
    ApplicationStatus,
    GrantApplication,
    GrantCall,
    GrantCallStatus,
    Idea,
)

router = APIRouter(route_class=DishkaRoute, tags=["admin"])

CALL_MISSING = "Nie znaleziono naboru."
APPLICATION_MISSING = "Nie znaleziono wniosku."
TEMPLATE_MISSING = "Nie ma takiego szablonu."
SECTIONS_NEEDED = "Dodaj sekcje wniosku albo wczytaj szablon ROPS."
DATES = "Data zamknięcia musi być późniejsza niż data otwarcia."
KEYS_LOCKED = "Ten nabór ma już wnioski: nie można zmienić kluczy sekcji."
HAS_APPLICATIONS = "Ten nabór ma już wnioski: zamiast usuwać, anuluj go."
DRAFT_APPLICATION = "Wniosek nie został jeszcze złożony."
SUBSCRIBER_MISSING = "Nie znaleziono subskrybenta."

PageNumber = Annotated[int, Query(ge=1, le=10_000)]
PerPage = Annotated[int, Query(ge=1, le=100)]


async def call_or_404(session: AsyncSession, call_id: uuid.UUID) -> GrantCall:
    call = await session.get(GrantCall, call_id)
    if call is None:
        raise not_found(CALL_MISSING)
    return call


async def publish_call(session: AsyncSession, call: GrantCall) -> AdminGrantCall:
    out = await calls.admin_out(session, call)
    bus.publish("grant_call.updated", out.model_dump(mode="json"))
    return out


@router.get("/grant-templates")
async def templates() -> list[GrantTemplateOut]:
    return [
        GrantTemplateOut(
            slug=t.slug,
            title=t.title,
            description=t.description,
            source_url=t.source_url,
            sections=list(t.sections),
        )
        for t in TEMPLATES.values()
    ]


@router.get("/grant-calls")
async def list_calls(
    session: FromDishka[AsyncSession],
    status: GrantCallStatus | None = None,
    page: PageNumber = 1,
    per_page: PerPage = 20,
) -> CallPage:
    items, total = await calls.list_admin(session, status, page, per_page)
    return CallPage(items=items, total=total, page=page, per_page=per_page)


@router.post("/grant-calls", status_code=status.HTTP_201_CREATED)
async def create_call(
    body: CallIn, admin: AdminPerson, session: FromDishka[AsyncSession]
) -> AdminGrantCall:
    sections = body.sections
    if body.template is not None:
        template = TEMPLATES.get(body.template)
        if template is None:
            error = invalid("template", TEMPLATE_MISSING)
            raise error
        sections = sections or list(template.sections)
    if not sections:
        error = invalid("sections", SECTIONS_NEEDED)
        raise error
    call = GrantCall(
        title=body.title,
        description=body.description,
        opens_at=body.opens_at,
        closes_at=body.closes_at,
        status=GrantCallStatus(body.status),
        source_url=str(body.source_url) if body.source_url else None,
        sections=[s.model_dump() for s in sections],
        template=body.template,
    )
    session.add(call)
    await session.flush()
    record(session, admin, "grant_call.create", target=("grant_call", call.id))
    await session.commit()
    await session.refresh(call)
    return await publish_call(session, call)


@router.get("/grant-calls/{call_id}")
async def get_call(
    call_id: uuid.UUID, session: FromDishka[AsyncSession]
) -> AdminGrantCall:
    return await calls.admin_out(session, await call_or_404(session, call_id))


@router.patch("/grant-calls/{call_id}")
async def update_call(
    call_id: uuid.UUID,
    body: CallPatch,
    admin: AdminPerson,
    session: FromDishka[AsyncSession],
    mailer: FromDishka[Mailer],
) -> AdminGrantCall:
    call = await call_or_404(session, call_id)
    fields = body.model_fields_set
    before = (call.opens_at, call.closes_at, call.status)
    if "sections" in fields:
        if not body.sections:
            error = invalid("sections", SECTIONS_NEEDED)
            raise error
        old = {raw["key"] for raw in call.sections}
        new = {s.key for s in body.sections}
        if old != new and await calls.has_applications(session, call.id):
            raise conflict(KEYS_LOCKED)
        call.sections = [s.model_dump() for s in body.sections]
    for name in ("title", "description", "opens_at", "closes_at", "status"):
        value = getattr(body, name)
        if name in fields and value is not None:
            setattr(call, name, value)
    if "source_url" in fields:
        call.source_url = str(body.source_url) if body.source_url else None
    if call.closes_at <= call.opens_at:
        error = invalid("closes_at", DATES)
        raise error
    dates_changed = (call.opens_at, call.closes_at) != before[:2]
    if dates_changed and call.opens_at > calls.now():
        call.notified_open_at = None
    session.add(call)
    record(
        session,
        admin,
        "grant_call.update",
        target=("grant_call", call.id),
        details={"fields": sorted(fields)},
    )
    await session.commit()
    await session.refresh(call)
    was_public = before[2] == GrantCallStatus.PUBLISHED
    if dates_changed and was_public and call.status == GrantCallStatus.PUBLISHED:
        spawn(notify.notify(call.id, mailer, opened=False))
    return await publish_call(session, call)


@router.delete("/grant-calls/{call_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_call(
    call_id: uuid.UUID, admin: AdminPerson, session: FromDishka[AsyncSession]
) -> None:
    call = await call_or_404(session, call_id)
    if await calls.has_applications(session, call.id):
        raise conflict(HAS_APPLICATIONS)
    record(session, admin, "grant_call.delete", target=("grant_call", call.id))
    await session.delete(call)
    await session.commit()


@router.get("/grant-calls/{call_id}/applications")
async def call_applications(
    call_id: uuid.UUID,
    session: FromDishka[AsyncSession],
    status: ApplicationStatus | None = None,
    page: PageNumber = 1,
    per_page: PerPage = 20,
) -> ApplicationPage:
    call = await call_or_404(session, call_id)
    items, total = await applications.list_for_call(
        session, call, status, page, per_page
    )
    return ApplicationPage(items=items, total=total, page=page, per_page=per_page)


async def application_or_404(
    session: AsyncSession, application_id: uuid.UUID
) -> tuple[GrantApplication, GrantCall, Idea]:
    found = await applications.load(session, application_id)
    if found is None:
        raise not_found(APPLICATION_MISSING)
    return found


@router.get("/applications/{application_id}")
async def get_application(
    application_id: uuid.UUID, session: FromDishka[AsyncSession]
) -> AdminApplication:
    return applications.admin_view(*await application_or_404(session, application_id))


@router.patch("/applications/{application_id}")
async def set_application_status(
    application_id: uuid.UUID,
    body: StatusIn,
    admin: AdminPerson,
    session: FromDishka[AsyncSession],
) -> AdminApplication:
    application, call, idea = await application_or_404(session, application_id)
    if application.status == ApplicationStatus.DRAFT:
        raise conflict(DRAFT_APPLICATION)
    previous = application.status
    application.status = ApplicationStatus(body.status)
    session.add(application)
    record(
        session,
        admin,
        "application.status",
        target=("grant_application", application.id),
        details={"from": previous, "to": body.status},
    )
    await session.commit()
    for row in (application, call, idea):
        await session.refresh(row)
    bus.publish(
        "application.updated",
        applications.summary(application, call, idea).model_dump(mode="json"),
    )
    return applications.admin_view(application, call, idea)


@router.get("/grant-subscribers")
async def list_subscribers(
    session: FromDishka[AsyncSession],
) -> subscribers.SubscriberList:
    return await subscribers.list_subscribers(session)


@router.delete(
    "/grant-subscribers/{subscriber_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_subscriber(
    subscriber_id: uuid.UUID, admin: AdminPerson, session: FromDishka[AsyncSession]
) -> None:
    if not await subscribers.remove(session, subscriber_id):
        raise not_found(SUBSCRIBER_MISSING)
    record(
        session,
        admin,
        "grant_subscriber.remove",
        target=("grant_subscriber", subscriber_id),
    )
    await session.commit()
