import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import STATUS_MESSAGES, ApiError, invalid, not_found
from api.limits import client_ip, persistent_rate_limit, rate_limit
from api.routers.api.modules.common import ai_guard
from services.bus import bus
from services.dialogue.service import token_opens
from services.grants import applications, calls, notify
from services.grants.pdf import render
from services.grants.schemas import (
    ApplicationCreated,
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
from services.modules.text import EMAIL as EMAIL_PATTERN
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
start_limit = persistent_rate_limit("grant_start", per_minute=3, per_day=30)
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
NOTHING_TO_DRAFT = "Napisz najpierw kilka zdań w dowolnej sekcji wniosku."
CONTACT_CONSENT = "Zaznacz zgodę na kontakt, jeśli podajesz adres e-mail."

IdeaToken = Annotated[str | None, Header(alias="X-Idea-Token", max_length=200)]
ApplicationToken = Annotated[
    str | None, Header(alias="X-Application-Token", max_length=200)
]
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


def opens(
    application: GrantApplication,
    idea: Idea | None,
    application_token: str | None,
    idea_token: str | None,
) -> bool:
    if applications.token_opens_application(application, application_token):
        return True
    return idea is not None and token_opens(idea, idea_token)


async def owned_application(
    session: AsyncSession,
    application_id: uuid.UUID,
    application_token: str | None,
    idea_token: str | None,
) -> tuple[GrantApplication, GrantCall, Idea | None]:
    found = await applications.load(session, application_id)
    if found is None or not opens(found[0], found[2], application_token, idea_token):
        raise not_found(APPLICATION_MISSING)
    return found


def check_contact(*, email: str | None, consent: bool | None) -> None:
    if email and not consent:
        error = invalid("contact_consent", CONTACT_CONSENT)
        raise error
    if email and not EMAIL_PATTERN.match(email):
        error = invalid("contact_email", EMAIL)
        raise error


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


@router.post(
    "/grant-calls/{call_id}/applications",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(start_limit)],
)
async def start_application(
    *,
    call_id: uuid.UUID,
    body: StartIn,
    response: Response,
    session: FromDishka[AsyncSession],
    x_idea_token: IdeaToken = None,
) -> ApplicationCreated:
    call = await published_call(session, call_id)
    check_contact(email=body.contact_email, consent=body.contact_consent)
    idea = None
    if body.idea_id is not None:
        idea = await session.get(Idea, body.idea_id)
        if idea is None or not token_opens(idea, x_idea_token):
            raise not_found(IDEA_MISSING)
        existing = await applications.find(session, call.id, idea.id)
        if existing is None and not calls.is_open(call):
            raise call_not_open()
    elif not calls.is_open(call):
        raise call_not_open()
    application, token, created = await applications.start(session, call, idea)
    if body.contact_email is not None or body.contact_consent is not None:
        applications.set_contact(
            application, email=body.contact_email, consent=body.contact_consent
        )
        session.add(application)
        await session.commit()
    for row in (application, call, *([idea] if idea else [])):
        await session.refresh(row)
    if not created:
        response.status_code = status.HTTP_200_OK
    return ApplicationCreated(
        **applications.view(application, call, idea).model_dump(), edit_token=token
    )


@router.get("/applications/{application_id}")
async def get_application(
    application_id: uuid.UUID,
    session: FromDishka[AsyncSession],
    _: ReadLimited,
    x_application_token: ApplicationToken = None,
    x_idea_token: IdeaToken = None,
) -> ApplicationOut:
    application, call, idea = await owned_application(
        session, application_id, x_application_token, x_idea_token
    )
    return applications.view(application, call, idea)


@router.patch("/applications/{application_id}", dependencies=[Depends(edit_limit)])
async def edit_application(
    application_id: uuid.UUID,
    body: SectionsPatch,
    session: FromDishka[AsyncSession],
    x_application_token: ApplicationToken = None,
    x_idea_token: IdeaToken = None,
) -> ApplicationOut:
    application, call, idea = await owned_application(
        session, application_id, x_application_token, x_idea_token
    )
    if application.status != ApplicationStatus.DRAFT:
        raise locked()
    check_contact(email=body.contact_email, consent=body.contact_consent)
    try:
        applications.edit_sections(application, call, body.sections)
    except applications.SectionError as e:
        raise section_error(e) from None
    if "contact_email" in body.model_fields_set or (
        "contact_consent" in body.model_fields_set
    ):
        applications.set_contact(
            application, email=body.contact_email, consent=body.contact_consent
        )
    session.add(application)
    await session.commit()
    for row in (application, call, *([idea] if idea else [])):
        await session.refresh(row)
    return applications.view(application, call, idea)


async def run_suggest(  # noqa: PLR0913
    *,
    application_id: uuid.UUID,
    body: RedraftIn,
    request: Request,
    session: AsyncSession,
    application_token: str | None,
    idea_token: str | None,
) -> ApplicationOut:
    application, call, idea = await owned_application(
        session, application_id, application_token, idea_token
    )
    if application.status != ApplicationStatus.DRAFT:
        raise locked()
    if not calls.is_open(call):
        raise call_not_open()
    draft_limit.check(client_ip(request))
    async with ai_guard():
        try:
            application = await applications.suggest(
                session, application, call, idea, body.keys
            )
        except applications.SectionError as e:
            raise section_error(e) from None
        except applications.NothingToDraftError:
            raise ApiError(
                status.HTTP_409_CONFLICT, "nothing_to_draft", NOTHING_TO_DRAFT
            ) from None
    await session.refresh(call)
    if idea is not None:
        await session.refresh(idea)
    return applications.view(application, call, idea)


@router.post("/applications/{application_id}/suggest")
async def suggest_application(  # noqa: PLR0913
    *,
    application_id: uuid.UUID,
    body: RedraftIn,
    request: Request,
    session: FromDishka[AsyncSession],
    x_application_token: ApplicationToken = None,
    x_idea_token: IdeaToken = None,
) -> ApplicationOut:
    return await run_suggest(
        application_id=application_id,
        body=body,
        request=request,
        session=session,
        application_token=x_application_token,
        idea_token=x_idea_token,
    )


@router.post("/applications/{application_id}/redraft")
async def redraft_application(  # noqa: PLR0913
    *,
    application_id: uuid.UUID,
    body: RedraftIn,
    request: Request,
    session: FromDishka[AsyncSession],
    x_application_token: ApplicationToken = None,
    x_idea_token: IdeaToken = None,
) -> ApplicationOut:
    return await run_suggest(
        application_id=application_id,
        body=body,
        request=request,
        session=session,
        application_token=x_application_token,
        idea_token=x_idea_token,
    )


@router.post(
    "/applications/{application_id}/submit", dependencies=[Depends(edit_limit)]
)
async def submit_application(
    application_id: uuid.UUID,
    session: FromDishka[AsyncSession],
    x_application_token: ApplicationToken = None,
    x_idea_token: IdeaToken = None,
) -> ApplicationOut:
    application, call, idea = await owned_application(
        session, application_id, x_application_token, x_idea_token
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
    for row in (application, call, *([idea] if idea else [])):
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
    x_application_token: ApplicationToken = None,
    x_idea_token: IdeaToken = None,
) -> Response:
    found = await applications.load(session, application_id)
    if found is None:
        raise not_found(APPLICATION_MISSING)
    application, call, idea = found
    if not (
        applications.pdf_key_matches(application.id, key)
        or opens(application, idea, x_application_token, x_idea_token)
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
