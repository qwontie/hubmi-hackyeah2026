import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Header, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import not_found
from api.limits import rate_limit
from api.security import AdminPerson
from services.bus import bus
from services.modules import Page, token_matches
from services.tester import (
    AdminFeedback,
    AdminTestSignup,
    Created,
    FeedbackIn,
    FeedbackOut,
    FeedbackSummary,
    ImprovementIn,
    InnovationFeedback,
    TestSignupIn,
    TestSignupPatch,
    repository,
)
from utils.db.models.feedback import FeedbackKind
from utils.db.models.test_signup import SignupStatus, TesterRole

from .common import (
    PageNumber,
    PerPage,
    ReadLimited,
    consented_email,
    innovation_or_404,
    optional_text,
    required_text,
)

public = APIRouter(route_class=DishkaRoute, tags=["tester"])
admin = APIRouter(route_class=DishkaRoute, tags=["tester"])

vote_limit = rate_limit("feedback", per_minute=20, per_day=200)
improvement_limit = rate_limit("improvement", per_minute=5, per_day=30)
signup_limit = rate_limit("test_signup", per_minute=5, per_day=20)

IMPROVEMENT_MIN = 10
NEED_MISSING = "Nie znaleziono tego zgłoszenia."


@public.get("/innovations/{slug}/feedback")
async def feedback_summary(
    slug: str, session: FromDishka[AsyncSession], _: ReadLimited
) -> FeedbackSummary:
    innovation = await innovation_or_404(session, slug)
    return await repository.summary(session, innovation.id)


@public.post(
    "/innovations/{slug}/feedback",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(vote_limit)],
)
async def post_feedback(
    slug: str,
    body: FeedbackIn,
    session: FromDishka[AsyncSession],
    x_need_token: Annotated[str | None, Header()] = None,
) -> FeedbackOut:
    innovation = await innovation_or_404(session, slug)
    comment = optional_text("comment", body.comment)
    if body.need_id is not None:
        expected = await repository.need_token_hash(session, body.need_id)
        if expected is None or not token_matches(expected, x_need_token):
            raise not_found(NEED_MISSING)
    feedback = await repository.add_vote(
        session,
        innovation_id=innovation.id,
        kind=FeedbackKind(body.kind),
        need_id=body.need_id,
        comment=comment,
    )
    bus.publish("feedback.created", repository.admin_feedback(feedback, innovation))
    return FeedbackOut(
        id=feedback.id,
        kind=feedback.kind,
        summary=await repository.summary(session, innovation.id),
    )


@public.post(
    "/innovations/{slug}/improvements",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(improvement_limit)],
)
async def post_improvement(
    slug: str, body: ImprovementIn, session: FromDishka[AsyncSession]
) -> Created:
    innovation = await innovation_or_404(session, slug)
    text = required_text("text", body.text, minimum=IMPROVEMENT_MIN)
    feedback = await repository.add_improvement(
        session, innovation_id=innovation.id, text_=text
    )
    bus.publish("feedback.created", repository.admin_feedback(feedback, innovation))
    return Created(id=feedback.id)


@public.post(
    "/innovations/{slug}/test-signup",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(signup_limit)],
)
async def post_test_signup(
    slug: str, body: TestSignupIn, session: FromDishka[AsyncSession]
) -> Created:
    innovation = await innovation_or_404(session, slug)
    email = consented_email(body.contact_email, body.contact_consent)
    signup = await repository.add_signup(
        session,
        innovation_id=innovation.id,
        who=body.who,
        organization=optional_text("organization", body.organization, line=True),
        powiat=body.powiat,
        contact_email=email,
        note=optional_text("note", body.note) or "",
    )
    bus.publish("test_signup.created", repository.admin_signup(signup, innovation))
    return Created(id=signup.id)


@admin.get("/feedback")
async def list_feedback(  # noqa: PLR0913
    *,
    _admin: AdminPerson,
    session: FromDishka[AsyncSession],
    kind: FeedbackKind | None = None,
    innovation: Annotated[str | None, Query(max_length=200)] = None,
    q: Annotated[str | None, Query(min_length=2, max_length=200)] = None,
    page: PageNumber = 1,
    per_page: PerPage = 20,
) -> Page[AdminFeedback]:
    return await repository.list_feedback(
        session, kind=kind, innovation=innovation, q=q, page=page, per_page=per_page
    )


@admin.get("/feedback/by-innovation")
async def feedback_by_innovation(
    _admin: AdminPerson,
    session: FromDishka[AsyncSession],
    sort: Annotated[str, Query(pattern="^(recent|does_not_fit|testers)$")] = "recent",
    page: PageNumber = 1,
    per_page: PerPage = 20,
) -> Page[InnovationFeedback]:
    return await repository.feedback_by_innovation(
        session, sort=sort, page=page, per_page=per_page
    )


@admin.get("/test-signups")
async def list_test_signups(  # noqa: PLR0913
    *,
    _admin: AdminPerson,
    session: FromDishka[AsyncSession],
    who: TesterRole | None = None,
    status: SignupStatus | None = None,
    powiat: Annotated[str | None, Query(max_length=60)] = None,
    innovation: Annotated[str | None, Query(max_length=200)] = None,
    page: PageNumber = 1,
    per_page: PerPage = 20,
) -> Page[AdminTestSignup]:
    return await repository.list_signups(
        session,
        who=who,
        status=status,
        powiat=powiat,
        innovation=innovation,
        page=page,
        per_page=per_page,
    )


@admin.patch("/test-signups/{signup_id}")
async def patch_test_signup(
    signup_id: uuid.UUID,
    body: TestSignupPatch,
    _admin: AdminPerson,
    session: FromDishka[AsyncSession],
) -> AdminTestSignup:
    signup = await repository.set_signup_status(session, signup_id, body.status)
    if signup is None:
        raise not_found()
    return signup
