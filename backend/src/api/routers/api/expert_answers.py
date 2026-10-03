import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Header, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import conflict, not_found
from api.limits import persistent_rate_limit, rate_limit
from api.routers.api.public.common import translate
from services.experts import AnswerIn, ExpertAnswerView, by_email
from services.needs import TextRejectedError
from services.tester.intake import checked_text, honeypot_check

router = APIRouter(route_class=DishkaRoute, tags=["expert-answers"])

read_limit = rate_limit("expert_answer_read", per_minute=60)
answer_limit = persistent_rate_limit("expert_answer", per_minute=5, per_day=30)

ANSWER_MIN = 10
ANSWER_MAX = 5000
MISSING = "Nie znaleziono tej sprawy. Link mógł wygasnąć, napisz do ROPS."
TOO_MANY = "Wysłano już najwięcej odpowiedzi do tej sprawy. Napisz do ROPS e-mailem."

ExpertToken = Annotated[str | None, Header(alias="X-Expert-Token", max_length=200)]


@router.get("/{assignment_id}", dependencies=[Depends(read_limit)])
async def answer_view(
    assignment_id: uuid.UUID,
    session: FromDishka[AsyncSession],
    token: ExpertToken = None,
) -> ExpertAnswerView:
    assignment = await by_email.opened(session, assignment_id, token)
    found = None if assignment is None else await by_email.view(session, assignment)
    if found is None:
        raise not_found(MISSING)
    return found


@router.post(
    "/{assignment_id}",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(answer_limit)],
)
async def post_answer(
    assignment_id: uuid.UUID,
    body: AnswerIn,
    session: FromDishka[AsyncSession],
    token: ExpertToken = None,
) -> ExpertAnswerView:
    try:
        honeypot_check(body.website)
        text = checked_text("body", body.body, minimum=ANSWER_MIN, maximum=ANSWER_MAX)
    except TextRejectedError as e:
        raise translate(e) from e
    assignment = await by_email.opened(session, assignment_id, token)
    if assignment is None:
        raise not_found(MISSING)
    try:
        result = await by_email.answer(session, assignment, text)
    except by_email.TooManyAnswersError:
        raise conflict(TOO_MANY) from None
    if result is None:
        raise not_found(MISSING)
    return result
