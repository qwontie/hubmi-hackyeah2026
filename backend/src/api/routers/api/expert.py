import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import not_found
from api.limits import rate_limit
from api.security import ExpertPerson
from services.experts import (
    AssignmentOut,
    ExpertAssignmentDetail,
    OpinionBody,
    OpinionOut,
)
from services.experts import service as experts
from services.mail import Mailer
from utils.db.models import AdminUser, Assignment, AssignmentStatus

router = APIRouter(route_class=DishkaRoute, tags=["expert"])

read_limit = rate_limit("expert_read", per_minute=120)
opinion_limit = rate_limit("expert_opinion", per_minute=30, per_day=500)

ASSIGNMENT_MISSING = "Nie znaleziono przydziału."


async def own(
    session: AsyncSession, expert: AdminUser, assignment_id: uuid.UUID
) -> Assignment:
    assignment = await session.get(Assignment, assignment_id)
    if assignment is None:
        raise not_found(ASSIGNMENT_MISSING)
    if assignment.expert_id != expert.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return assignment


@router.get("/assignments", dependencies=[Depends(read_limit)])
async def assignments(
    expert: ExpertPerson,
    session: FromDishka[AsyncSession],
    status: AssignmentStatus | None = None,
) -> list[AssignmentOut]:
    return await experts.for_expert(session, expert, status)


@router.get("/assignments/{assignment_id}", dependencies=[Depends(read_limit)])
async def assignment_detail(
    assignment_id: uuid.UUID, expert: ExpertPerson, session: FromDishka[AsyncSession]
) -> ExpertAssignmentDetail:
    found = await experts.detail(session, await own(session, expert, assignment_id))
    if found is None:
        raise not_found(ASSIGNMENT_MISSING)
    return found


@router.post(
    "/assignments/{assignment_id}/opinion",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(opinion_limit)],
)
async def write_opinion(
    assignment_id: uuid.UUID,
    body: OpinionBody,
    expert: ExpertPerson,
    session: FromDishka[AsyncSession],
    mailer: FromDishka[Mailer],
) -> OpinionOut:
    assignment = await own(session, expert, assignment_id)
    result = await experts.opinion(
        session,
        expert=expert,
        assignment=assignment,
        body=body.body,
        private_note=body.private_note,
        mailer=mailer,
    )
    if result is None:
        raise not_found(ASSIGNMENT_MISSING)
    return result
