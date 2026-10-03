import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import conflict, invalid, not_found
from api.security import AdminPerson
from services.experts import (
    AdminAssignment,
    AssignBody,
    AssignmentOut,
    ExpertContact,
    ExpertOut,
    ForwardBody,
    by_email,
)
from services.experts import service as experts
from services.mail import Mailer
from services.modules import normalize_email
from utils.db.models import Assignment, Idea, Need

router = APIRouter(route_class=DishkaRoute, tags=["admin"])

IDEA_MISSING = "Nie znaleziono pomysłu."
NEED_MISSING = "Nie znaleziono zgłoszenia."
ASSIGNMENT_MISSING = "Nie znaleziono przydziału."
NOT_EXPERT = "Wybierz eksperta z listy."
ALREADY = "Ten ekspert ma już tę sprawę."
EMAIL_MESSAGE = "Wpisz poprawny adres e-mail."
NOT_BY_EMAIL = "Ten ekspert ma konto, nie wysyłamy mu linku."


async def idea_or_404(session: AsyncSession, idea_id: uuid.UUID) -> Idea:
    idea = await session.get(Idea, idea_id)
    if idea is None:
        raise not_found(IDEA_MISSING)
    return idea


async def need_or_404(session: AsyncSession, need_id: uuid.UUID) -> Need:
    need = await session.get(Need, need_id)
    if need is None:
        raise not_found(NEED_MISSING)
    return need


async def assign_item(
    session: AsyncSession,
    admin: AdminPerson,
    item: Idea | Need,
    body: AssignBody,
    mailer: Mailer,
) -> AssignmentOut:
    try:
        return await experts.assign(
            session,
            admin=admin,
            item=item,
            expert_id=body.expert_id,
            note=body.note,
            mailer=mailer,
        )
    except experts.NotAnExpertError:
        error = invalid("expert_id", NOT_EXPERT)
        raise error from None
    except experts.AlreadyAssignedError:
        raise conflict(ALREADY) from None


@router.get("/experts")
async def list_experts(session: FromDishka[AsyncSession]) -> list[ExpertOut]:
    return await experts.experts(session)


@router.get("/experts/contacts")
async def expert_contacts(session: FromDishka[AsyncSession]) -> list[ExpertContact]:
    return await by_email.contacts(session)


async def forward_item(
    session: AsyncSession,
    admin: AdminPerson,
    item: Idea | Need,
    body: ForwardBody,
    mailer: Mailer,
) -> AssignmentOut:
    email = normalize_email(body.email)
    if email is None:
        error = invalid("email", EMAIL_MESSAGE)
        raise error
    try:
        return await by_email.forward(
            session,
            admin=admin,
            item=item,
            email=email,
            name=body.name,
            expertise=body.expertise,
            note=body.note,
            mailer=mailer,
        )
    except experts.AlreadyAssignedError:
        raise conflict(ALREADY) from None


@router.post("/ideas/{idea_id}/forward", status_code=status.HTTP_201_CREATED)
async def forward_idea(
    idea_id: uuid.UUID,
    body: ForwardBody,
    admin: AdminPerson,
    session: FromDishka[AsyncSession],
    mailer: FromDishka[Mailer],
) -> AssignmentOut:
    idea = await idea_or_404(session, idea_id)
    return await forward_item(session, admin, idea, body, mailer)


@router.post("/needs/{need_id}/forward", status_code=status.HTTP_201_CREATED)
async def forward_need(
    need_id: uuid.UUID,
    body: ForwardBody,
    admin: AdminPerson,
    session: FromDishka[AsyncSession],
    mailer: FromDishka[Mailer],
) -> AssignmentOut:
    need = await need_or_404(session, need_id)
    return await forward_item(session, admin, need, body, mailer)


@router.post("/assignments/{assignment_id}/resend")
async def resend(
    assignment_id: uuid.UUID,
    admin: AdminPerson,
    session: FromDishka[AsyncSession],
    mailer: FromDishka[Mailer],
) -> AssignmentOut:
    assignment = await session.get(Assignment, assignment_id)
    if assignment is None:
        raise not_found(ASSIGNMENT_MISSING)
    try:
        result = await by_email.resend(session, admin, assignment, mailer)
    except by_email.NotByEmailError:
        raise conflict(NOT_BY_EMAIL) from None
    if result is None:
        raise not_found(ASSIGNMENT_MISSING)
    return result


@router.post("/ideas/{idea_id}/assign", status_code=status.HTTP_201_CREATED)
async def assign_idea(
    idea_id: uuid.UUID,
    body: AssignBody,
    admin: AdminPerson,
    session: FromDishka[AsyncSession],
    mailer: FromDishka[Mailer],
) -> AssignmentOut:
    idea = await idea_or_404(session, idea_id)
    return await assign_item(session, admin, idea, body, mailer)


@router.post("/needs/{need_id}/assign", status_code=status.HTTP_201_CREATED)
async def assign_need(
    need_id: uuid.UUID,
    body: AssignBody,
    admin: AdminPerson,
    session: FromDishka[AsyncSession],
    mailer: FromDishka[Mailer],
) -> AssignmentOut:
    need = await need_or_404(session, need_id)
    return await assign_item(session, admin, need, body, mailer)


@router.get("/ideas/{idea_id}/assignments")
async def idea_assignments(
    idea_id: uuid.UUID, session: FromDishka[AsyncSession]
) -> list[AdminAssignment]:
    return await experts.for_item(session, await idea_or_404(session, idea_id))


@router.get("/needs/{need_id}/assignments")
async def need_assignments(
    need_id: uuid.UUID, session: FromDishka[AsyncSession]
) -> list[AdminAssignment]:
    return await experts.for_item(session, await need_or_404(session, need_id))


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign(
    assignment_id: uuid.UUID, admin: AdminPerson, session: FromDishka[AsyncSession]
) -> None:
    assignment = await session.get(Assignment, assignment_id)
    if assignment is None:
        raise not_found(ASSIGNMENT_MISSING)
    await experts.unassign(session, admin, assignment)
