import hashlib
import hmac
import re
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Header, Query, Request, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import invalid, not_found
from api.limits import PER_DAY, RateLimiter, Rule, client_ip, rate_limit
from api.security import AdminPerson
from services.bus import bus
from services.modules import Page
from services.needs.tokens import token_matches
from services.tester import (
    AdminFeedback,
    AdminTestSignup,
    Created,
    FeedbackIn,
    FeedbackOut,
    FeedbackSummary,
    ImprovementIn,
    InnovationFeedback,
    VoteRemoved,
    repository,
)
from utils.db.models.feedback import FeedbackKind
from utils.db.models.test_signup import SignupStatus, TesterRole
from utils.env import env

from . import volunteers
from .common import (
    PageNumber,
    PerPage,
    PowiatFilter,
    ReadLimited,
    SearchFilter,
    SlugFilter,
    innovation_or_404,
    optional_text,
    required_text,
)

public = APIRouter(route_class=DishkaRoute, tags=["tester"])
admin = APIRouter(route_class=DishkaRoute, tags=["tester"])
public.include_router(volunteers.public)
admin.include_router(volunteers.admin)

vote_limit = rate_limit("feedback", per_minute=20, per_day=200)
improvement_limit = rate_limit("improvement", per_minute=5, per_day=30)
card_limit = RateLimiter("vote_card", Rule(10, PER_DAY))

IMPROVEMENT_MIN = 10
NEED_MISSING = "Nie znaleziono tego zgłoszenia."
VOTER_ID = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
VOTER_MESSAGE = "Nieprawidłowy identyfikator urządzenia."

VoterHeader = Annotated[str | None, Header(max_length=200)]


def voter_hash(request: Request, voter_id: str | None) -> str:
    if voter_id is None:
        key = f"ip:{client_ip(request)}"
    elif VOTER_ID.match(voter_id):
        key = f"device:{voter_id}"
    else:
        error = invalid("x_voter_id", VOTER_MESSAGE)
        raise error
    secret = env.auth.secret.get_secret_value().encode()
    return hmac.new(secret, f"voter:{key}".encode(), hashlib.sha256).hexdigest()


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
async def post_feedback(  # noqa: PLR0913
    *,
    slug: str,
    body: FeedbackIn,
    request: Request,
    session: FromDishka[AsyncSession],
    x_need_token: Annotated[str | None, Header()] = None,
    x_voter_id: VoterHeader = None,
) -> FeedbackOut:
    innovation = await innovation_or_404(session, slug)
    voter = voter_hash(request, x_voter_id)
    comment = optional_text("comment", body.comment)
    if body.need_id is not None:
        expected = await repository.need_token_hash(session, body.need_id)
        if expected is None or not token_matches(x_need_token, expected):
            raise not_found(NEED_MISSING)
    card_limit.check(f"{client_ip(request)}:{innovation.id}")
    feedback = await repository.add_vote(
        session,
        innovation_id=innovation.id,
        kind=FeedbackKind(body.kind),
        need_id=body.need_id,
        voter_hash=voter,
        comment=comment,
    )
    bus.publish("feedback.created", repository.admin_feedback(feedback, innovation))
    summary = await repository.summary(session, innovation.id)
    return FeedbackOut(
        id=feedback.id,
        kind=feedback.kind,
        votes=repository.votes_of(summary),
        summary=summary,
    )


@public.delete("/innovations/{slug}/feedback", dependencies=[Depends(vote_limit)])
async def delete_feedback(
    slug: str,
    request: Request,
    session: FromDishka[AsyncSession],
    x_voter_id: VoterHeader = None,
) -> VoteRemoved:
    innovation = await innovation_or_404(session, slug)
    await repository.remove_vote(
        session, innovation_id=innovation.id, voter_hash=voter_hash(request, x_voter_id)
    )
    summary = await repository.summary(session, innovation.id)
    return VoteRemoved(votes=repository.votes_of(summary), summary=summary)


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


@admin.get("/feedback")
async def list_feedback(  # noqa: PLR0913
    *,
    _admin: AdminPerson,
    session: FromDishka[AsyncSession],
    kind: FeedbackKind | None = None,
    innovation: SlugFilter = None,
    q: SearchFilter = None,
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
    powiat: PowiatFilter = None,
    innovation: SlugFilter = None,
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
