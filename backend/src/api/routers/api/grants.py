import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import STATUS_MESSAGES, ApiError, invalid, not_found
from api.limits import client_ip, rate_limit
from api.routers.api.modules.common import ai_guard
from services.bus import bus
from services.dialogue.service import token_opens
from services.grants import applications, calls, notify
from services.grants.pdf import render
from services.grants.schemas import (
    ApplicationOut,
    GrantCallOut,
    Phase,
    RedraftIn,
    SectionsPatch,
    StartIn,
    SubscribeIn,
    SubscriptionOut,
    TokenIn,
)
from services.mail import Mailer
from utils.db.models import (
    ApplicationStatus,
    GrantApplication,
    GrantCall,
    GrantCallStatus,
    Idea,
)

router = APIRouter(route_class=DishkaRoute, tags=["grants"])

read_limit = rate_limit("grant_read", per_minute=120)
draft_limit = rate_limit("grant_draft", per_minute=2, per_day=10)
edit_limit = rate_limit("grant_edit", per_minute=30, per_day=500)
subscribe_limit = rate_limit("grant_subscribe", per_minute=3, per_day=10)
token_limit = rate_limit("grant_token", per_minute=10, per_day=100)

CALL_MISSING = "Nie znaleziono naboru."
APPLICATION_MISSING = "Nie znaleziono wniosku."
IDEA_MISSING = "Nie znaleziono tego pomysłu."
NOT_OPEN = "Ten nabór nie przyjmuje teraz wniosków."
LOCKED = "Wniosek został już złożony i nie można go zmieniać."
CONSENT = "Zaznacz zgodę, abyśmy mogli wysyłać powiadomienia."
EMAIL = "Wpisz poprawny adres e-mail."
LINK_INVALID = "Ten link jest nieprawidłowy albo wygasł."

IdeaToken = Annotated[str | None, Header(alias="X-Idea-Token", max_length=200)]
PdfKey = Annotated[str | None, Query(max_length=64, pattern=r"^[A-Za-z0-9_-]*$")]
ReadLimited = Annotated[None, Depends(read_limit)]


def call_not_open() -> ApiError:
    return ApiError(status.HTTP_409_CONFLICT, "call_not_open", NOT_OPEN)


def locked() -> ApiError:
    return ApiError(status.HTTP_409_CONFLICT, "conflict", LOCKED)


async def published_call(session: AsyncSession, call_id: uuid.UUID) -> GrantCall:
    call = await session.get(GrantCall, call_id)
    if call is None or call.status != GrantCallStatus.PUBLISHED:
        raise not_found(CALL_MISSING)
    return call


async def owned_application(
    session: AsyncSession, application_id: uuid.UUID, token: str | None
) -> tuple[GrantApplication, GrantCall, Idea]:
    found = await applications.load(session, application_id)
    if found is None or not token_opens(found[2], token):
        raise not_found(APPLICATION_MISSING)
    return found


def section_error(error: applications.SectionError) -> ApiError:
    return invalid(error.field, error.message)


@router.get("/grant-calls")
async def list_calls(
    session: FromDishka[AsyncSession], _: ReadLimited, phase: Phase | None = None
) -> list[GrantCallOut]:
    if phase == "closed":
        return []
    return await calls.list_public(session, phase)


@router.get("/grant-calls/{call_id}")
async def get_call(
    call_id: uuid.UUID, session: FromDishka[AsyncSession], _: ReadLimited
) -> GrantCallOut:
    return calls.public_out(await published_call(session, call_id))


@router.post("/grant-calls/subscribe", status_code=status.HTTP_202_ACCEPTED)
async def subscribe(
    body: SubscribeIn,
    request: Request,
    session: FromDishka[AsyncSession],
    mailer: FromDishka[Mailer],
) -> SubscriptionOut:
    if not body.consent:
        error = invalid("consent", CONSENT)
        raise error
    subscribe_limit.check(client_ip(request))
    try:
        await notify.subscribe(session, body.email, mailer)
    except notify.InvalidEmailError:
        error = invalid("email", EMAIL)
        raise error from None
    return SubscriptionOut(status="pending")


@router.post("/grant-calls/subscription/confirm", dependencies=[Depends(token_limit)])
async def confirm(body: TokenIn, session: FromDishka[AsyncSession]) -> SubscriptionOut:
    if not await notify.confirm(session, body.token):
        raise not_found(LINK_INVALID)
    return SubscriptionOut(status="confirmed")


@router.post(
    "/grant-calls/subscription/unsubscribe", dependencies=[Depends(token_limit)]
)
async def unsubscribe(
    body: TokenIn, session: FromDishka[AsyncSession]
) -> SubscriptionOut:
    if not await notify.unsubscribe(session, body.token):
        raise not_found(LINK_INVALID)
    return SubscriptionOut(status="unsubscribed")


@router.post("/grant-calls/{call_id}/applications", status_code=status.HTTP_201_CREATED)
async def start_application(  # noqa: PLR0913
    *,
    call_id: uuid.UUID,
    body: StartIn,
    request: Request,
    response: Response,
    session: FromDishka[AsyncSession],
    x_idea_token: IdeaToken = None,
) -> ApplicationOut:
    call = await published_call(session, call_id)
    idea = await session.get(Idea, body.idea_id)
    if idea is None or not token_opens(idea, x_idea_token):
        raise not_found(IDEA_MISSING)
    existing = await applications.find(session, call.id, idea.id)
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return applications.view(existing, call, idea)
    if not calls.is_open(call):
        raise call_not_open()
    draft_limit.check(client_ip(request))
    async with ai_guard():
        application, created = await applications.start(session, call, idea)
    await session.refresh(call)
    await session.refresh(idea)
    if not created:
        response.status_code = status.HTTP_200_OK
    return applications.view(application, call, idea)


@router.get("/applications/{application_id}")
async def get_application(
    application_id: uuid.UUID,
    session: FromDishka[AsyncSession],
    _: ReadLimited,
    x_idea_token: IdeaToken = None,
) -> ApplicationOut:
    application, call, idea = await owned_application(
        session, application_id, x_idea_token
    )
    return applications.view(application, call, idea)


@router.patch("/applications/{application_id}", dependencies=[Depends(edit_limit)])
async def edit_application(
    application_id: uuid.UUID,
    body: SectionsPatch,
    session: FromDishka[AsyncSession],
    x_idea_token: IdeaToken = None,
) -> ApplicationOut:
    application, call, idea = await owned_application(
        session, application_id, x_idea_token
    )
    if application.status != ApplicationStatus.DRAFT:
        raise locked()
    try:
        applications.edit_sections(application, call, body.sections)
    except applications.SectionError as e:
        raise section_error(e) from None
    session.add(application)
    await session.commit()
    for row in (application, call, idea):
        await session.refresh(row)
    return applications.view(application, call, idea)


@router.post("/applications/{application_id}/redraft")
async def redraft_application(
    application_id: uuid.UUID,
    body: RedraftIn,
    request: Request,
    session: FromDishka[AsyncSession],
    x_idea_token: IdeaToken = None,
) -> ApplicationOut:
    application, call, idea = await owned_application(
        session, application_id, x_idea_token
    )
    if application.status != ApplicationStatus.DRAFT:
        raise locked()
    if not calls.is_open(call):
        raise call_not_open()
    draft_limit.check(client_ip(request))
    async with ai_guard():
        try:
            application = await applications.redraft(
                session, application, call, idea, body.keys
            )
        except applications.SectionError as e:
            raise section_error(e) from None
    await session.refresh(call)
    await session.refresh(idea)
    return applications.view(application, call, idea)


@router.post(
    "/applications/{application_id}/submit", dependencies=[Depends(edit_limit)]
)
async def submit_application(
    application_id: uuid.UUID,
    session: FromDishka[AsyncSession],
    x_idea_token: IdeaToken = None,
) -> ApplicationOut:
    application, call, idea = await owned_application(
        session, application_id, x_idea_token
    )
    if application.status != ApplicationStatus.DRAFT:
        raise locked()
    if not calls.is_open(call):
        raise call_not_open()
    errors = applications.submit_errors(application, call)
    if errors:
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "validation_error",
            STATUS_MESSAGES[422],
            fields=errors,
        )
    applications.mark_submitted(application)
    session.add(application)
    await session.commit()
    for row in (application, call, idea):
        await session.refresh(row)
    bus.publish(
        "application.submitted",
        applications.summary(application, call, idea).model_dump(mode="json"),
    )
    return applications.view(application, call, idea)


@router.get(
    "/applications/{application_id}/export.pdf",
    response_class=Response,
    dependencies=[Depends(read_limit)],
)
async def export_pdf(
    application_id: uuid.UUID,
    session: FromDishka[AsyncSession],
    key: PdfKey = None,
    x_idea_token: IdeaToken = None,
) -> Response:
    found = await applications.load(session, application_id)
    if found is None:
        raise not_found(APPLICATION_MISSING)
    application, call, idea = found
    if not (
        applications.pdf_key_matches(application.id, key)
        or token_opens(idea, x_idea_token)
    ):
        raise not_found(APPLICATION_MISSING)
    content = render(applications.view(application, call, idea))
    name = f"wniosek-{application.number}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{name}"',
            "Cache-Control": "private, no-store",
        },
    )
