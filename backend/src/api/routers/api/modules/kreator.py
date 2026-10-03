import uuid
from datetime import UTC, datetime
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Header, Request, status
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import conflict, invalid, not_found
from api.limits import client_ip, rate_limit
from api.security import AdminPerson
from services.ai import AiUnavailableError, embed_query
from services.ai.costs import AiBudgetExceededError
from services.bus import bus
from services.kreator import (
    CANVAS_LABELS,
    STAGE_NAMES,
    AdminIdea,
    AdminIdeaDetail,
    AssistIn,
    AssistOut,
    AuthorIdea,
    Canvas,
    CanvasField,
    IdeaCreated,
    IdeaIn,
    IdeaPatch,
    IdeaStatusPatch,
    PublicIdea,
    StageOption,
    UnclearDraftError,
    assist,
    author_text,
    repository,
)
from services.modules import Page, clean, clean_line, is_meaningful
from services.needs.tokens import new_token, token_matches
from services.search import nearest_innovations
from utils.db.models.idea import Idea, IdeaStage, IdeaStatus

from .common import (
    PageNumber,
    PerPage,
    PowiatFilter,
    ReadLimited,
    SearchFilter,
    ai_guard,
    optional_email,
    powiat_name,
    required_text,
    text_too_short,
    unclear,
)

public = APIRouter(route_class=DishkaRoute, tags=["kreator"])
admin = APIRouter(route_class=DishkaRoute, tags=["kreator"])

create_limit = rate_limit("idea_create", per_minute=5, per_day=20)
assist_limit = rate_limit("idea_assist", per_minute=10, per_day=60)

TITLE_MIN = 5
ESSENCE_MIN = 20
FOR_WHOM_MIN = 3
DRAFT_MIN = 20
ASSIST_CANDIDATES = 5
OFF_TOPIC = "Opisz pomysł, który pomoże ludziom albo społeczności."
EMAIL_NEEDED = "Podaj adres e-mail, abyśmy mogli odpisać."
IDEA_MISSING = "Nie znaleziono tego pomysłu."
LOCKED = "Ten pomysł jest już rozpatrzony. Napisz do nas, jeśli chcesz coś zmienić."

IdeaToken = Annotated[str | None, Header(alias="X-Idea-Token")]


class IdeaOptions(BaseModel):
    stages: list[StageOption]
    canvas_fields: list[CanvasField]


def clean_canvas(canvas: Canvas | None) -> Canvas:
    if canvas is None:
        return Canvas()
    return Canvas.model_validate(
        {key: loose(value) for key, value in canvas.model_dump().items()}
    )


def loose(value: str | None, *, line: bool = False) -> str | None:
    if value is None:
        return None
    text = clean_line(value) if line else clean(value)
    return text or None


def set_contact(idea: Idea, body: IdeaPatch) -> None:
    fields = body.model_fields_set
    if "contact_consent" in fields and not body.contact_consent:
        email = None
    elif "contact_email" in fields:
        consent = (
            bool(body.contact_consent)
            if "contact_consent" in fields
            else idea.contact_consent
        )
        email = optional_email(body.contact_email, consent)
    else:
        email = idea.contact_email
        if email is None:
            error = invalid("contact_email", EMAIL_NEEDED)
            raise error
    if email != idea.contact_email:
        idea.consent_at = datetime.now(UTC) if email else None
    idea.contact_email = email
    idea.contact_consent = email is not None


async def owned_idea(
    session: AsyncSession, idea_id: uuid.UUID, token: str | None
) -> Idea | None:
    idea = await repository.get(session, idea_id)
    if idea is None or not token_matches(token, idea.edit_token_hash):
        return None
    return idea


@public.get("/ideas/options")
async def idea_options(_: ReadLimited) -> IdeaOptions:
    return IdeaOptions(
        stages=[
            StageOption(slug=slug, name=name) for slug, name in STAGE_NAMES.items()
        ],
        canvas_fields=[
            CanvasField(field=field, name=name) for field, name in CANVAS_LABELS.items()
        ],
    )


@public.post("/ideas", status_code=status.HTTP_201_CREATED)
async def create_idea(
    body: IdeaIn, request: Request, session: FromDishka[AsyncSession]
) -> IdeaCreated:
    title = required_text("title", body.title, minimum=TITLE_MIN).replace("\n", " ")
    essence = required_text("essence", body.essence, minimum=ESSENCE_MIN)
    for_whom = required_text("for_whom", body.for_whom, minimum=FOR_WHOM_MIN)
    canvas = clean_canvas(body.canvas)
    powiat_name("powiat", body.powiat)
    email = optional_email(body.contact_email, body.contact_consent)
    create_limit.check(client_ip(request))
    token, token_hash = new_token()
    idea = await repository.create(
        session,
        title=title,
        essence=essence,
        for_whom=for_whom,
        stage=body.stage,
        canvas=canvas,
        powiat=body.powiat,
        contact_email=email,
        token_hash=token_hash,
    )
    similar_ideas = []
    similar_innovations = []
    if idea.embedding is not None:
        vector = list(idea.embedding)
        similar_ideas = await repository.similar_ideas(
            session, vector, exclude_id=idea.id
        )
        similar_innovations = await repository.similar_innovations(session, vector)
    bus.publish("idea.created", repository.admin_view(idea))
    return IdeaCreated(
        id=idea.id,
        number=idea.number or 0,
        edit_token=token,
        similar_ideas=similar_ideas,
        similar_innovations=similar_innovations,
    )


@public.post("/ideas/assist")
async def assist_idea(
    body: AssistIn, request: Request, session: FromDishka[AsyncSession]
) -> AssistOut:
    draft = AssistIn.model_validate(
        {
            "title": loose(body.title, line=True),
            "essence": loose(body.essence),
            "for_whom": loose(body.for_whom),
            "stage": body.stage,
            "canvas": clean_canvas(body.canvas),
            "answers": [
                {"question": clean_line(a.question), "answer": text}
                for a in body.answers
                if (text := loose(a.answer))
            ],
        }
    )
    own = author_text(draft)
    error = None
    if len(own) < DRAFT_MIN:
        error = text_too_short("essence", DRAFT_MIN)
    elif not is_meaningful(own):
        error = unclear("essence")
    if error is not None:
        raise error
    assist_limit.check(client_ip(request))
    candidates = []
    try:
        vector = await embed_query(own, kind="idea_assist_embed")
        candidates = [
            row
            for row, _similarity in await nearest_innovations(
                session, vector, limit=ASSIST_CANDIDATES
            )
        ]
    except (AiUnavailableError, AiBudgetExceededError):
        candidates = []
    await session.commit()
    async with ai_guard():
        try:
            return await assist(draft, candidates)
        except UnclearDraftError:
            error = unclear("essence", OFF_TOPIC)
            raise error from None


@public.get("/ideas")
async def list_ideas(
    session: FromDishka[AsyncSession],
    _: ReadLimited,
    stage: IdeaStage | None = None,
    page: PageNumber = 1,
    per_page: PerPage = 20,
) -> Page[PublicIdea]:
    return await repository.list_public(
        session, stage=stage, page=page, per_page=per_page
    )


@public.get("/ideas/{idea_id}")
async def get_idea(
    idea_id: uuid.UUID,
    session: FromDishka[AsyncSession],
    _: ReadLimited,
    x_idea_token: IdeaToken = None,
) -> AuthorIdea | PublicIdea:
    idea = await repository.get(session, idea_id)
    if idea is None:
        raise not_found(IDEA_MISSING)
    if token_matches(x_idea_token, idea.edit_token_hash):
        return repository.author_view(idea)
    if idea.status in repository.PUBLIC_STATUSES:
        return repository.public_view(idea)
    raise not_found(IDEA_MISSING)


@public.patch("/ideas/{idea_id}")
async def patch_idea(
    idea_id: uuid.UUID,
    body: IdeaPatch,
    session: FromDishka[AsyncSession],
    x_idea_token: IdeaToken = None,
) -> AuthorIdea:
    idea = await owned_idea(session, idea_id, x_idea_token)
    if idea is None:
        raise not_found(IDEA_MISSING)
    if idea.status not in repository.EDITABLE_STATUSES:
        raise conflict(LOCKED)
    fields = body.model_fields_set
    reembed = False
    if "title" in fields and body.title is not None:
        idea.title = required_text("title", body.title, minimum=TITLE_MIN).replace(
            "\n", " "
        )
        reembed = True
    if "essence" in fields and body.essence is not None:
        idea.essence = required_text("essence", body.essence, minimum=ESSENCE_MIN)
        reembed = True
    if "for_whom" in fields and body.for_whom is not None:
        idea.for_whom = required_text("for_whom", body.for_whom, minimum=FOR_WHOM_MIN)
        reembed = True
    if "stage" in fields and body.stage is not None:
        idea.stage = body.stage
    if "canvas" in fields:
        idea.canvas = clean_canvas(body.canvas).model_dump(exclude_none=True)
    if "powiat" in fields:
        powiat_name("powiat", body.powiat)
        idea.powiat = body.powiat
    if "contact_email" in fields or "contact_consent" in fields:
        set_contact(idea, body)
    idea = await repository.save(session, idea, reembed=reembed)
    bus.publish("idea.updated", repository.admin_view(idea))
    return repository.author_view(idea)


@admin.get("/ideas")
async def admin_list_ideas(  # noqa: PLR0913
    *,
    _admin: AdminPerson,
    session: FromDishka[AsyncSession],
    status: IdeaStatus | None = None,
    stage: IdeaStage | None = None,
    powiat: PowiatFilter = None,
    q: SearchFilter = None,
    page: PageNumber = 1,
    per_page: PerPage = 20,
) -> Page[AdminIdea]:
    return await repository.list_admin(
        session,
        status=status,
        stage=stage,
        powiat=powiat,
        q=q,
        page=page,
        per_page=per_page,
    )


@admin.get("/ideas/{idea_id}")
async def admin_get_idea(
    idea_id: uuid.UUID, _admin: AdminPerson, session: FromDishka[AsyncSession]
) -> AdminIdeaDetail:
    idea = await repository.get(session, idea_id)
    if idea is None:
        raise not_found(IDEA_MISSING)
    return await repository.admin_detail(session, idea)


@admin.patch("/ideas/{idea_id}")
async def admin_patch_idea(
    idea_id: uuid.UUID,
    body: IdeaStatusPatch,
    _admin: AdminPerson,
    session: FromDishka[AsyncSession],
) -> AdminIdeaDetail:
    idea = await repository.get(session, idea_id)
    if idea is None:
        raise not_found(IDEA_MISSING)
    idea.status = body.status
    idea = await repository.save(session, idea, reembed=False)
    bus.publish("idea.updated", repository.admin_view(idea))
    return await repository.admin_detail(session, idea)
