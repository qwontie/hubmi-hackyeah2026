import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Request, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import not_found
from api.limits import client_ip, rate_limit
from api.security import AdminPerson
from services.ai.models import chat_model_name
from services.bus import bus
from services.middleman import (
    INSTITUTION_NAMES,
    AdaptationOut,
    AdaptIn,
    AdminAdaptation,
    InstitutionOption,
    InstitutionType,
    UnclearRequestError,
    generate_plan,
    repository,
)
from services.middleman.local import local_data
from services.modules import Page

from .common import (
    PageNumber,
    PerPage,
    PowiatFilter,
    ReadLimited,
    SlugFilter,
    ai_guard,
    innovation_or_404,
    powiat_name,
    required_text,
    unclear,
)

public = APIRouter(route_class=DishkaRoute, tags=["middleman"])
admin = APIRouter(route_class=DishkaRoute, tags=["middleman"])

adapt_limit = rate_limit("adapt", per_minute=3, per_day=20)

PLACE_MIN = 2
CONTEXT_MIN = 20
OFF_TOPIC = (
    "Opisz instytucję: kim są wasi odbiorcy, kto u was pracuje, jaki macie budżet."
)
ADAPTATION_MISSING = "Nie znaleziono tego planu."


@public.get("/institution-types")
async def institution_types(_: ReadLimited) -> list[InstitutionOption]:
    return [
        InstitutionOption(slug=kind, name=name)
        for kind, name in INSTITUTION_NAMES.items()
    ]


@public.post("/innovations/{slug}/adapt", status_code=status.HTTP_201_CREATED)
async def adapt(
    slug: str, body: AdaptIn, request: Request, session: FromDishka[AsyncSession]
) -> AdaptationOut:
    innovation = await innovation_or_404(session, slug)
    place = required_text("place", body.place, minimum=PLACE_MIN).replace("\n", " ")
    context = required_text("context", body.context, minimum=CONTEXT_MIN)
    powiat = powiat_name("powiat", body.powiat)
    adapt_limit.check(client_ip(request))
    candidates = await repository.candidates(session, innovation)
    local = await local_data(session, body.powiat, innovation)
    await session.commit()
    async with ai_guard():
        try:
            plan = await generate_plan(
                innovation=innovation,
                institution=body.institution_type,
                place=place,
                powiat_name=powiat,
                context=context,
                candidates=candidates,
                local=local,
            )
        except UnclearRequestError:
            error = unclear("context", OFF_TOPIC)
            raise error from None
    adaptation = await repository.store(
        session,
        innovation=innovation,
        institution_type=body.institution_type,
        place=place,
        powiat=body.powiat,
        context=context,
        plan=plan,
        model=chat_model_name(),
    )
    bus.publish("adaptation.created", adaptation)
    return adaptation


@public.get("/adaptations/{adaptation_id}")
async def get_adaptation(
    adaptation_id: uuid.UUID, session: FromDishka[AsyncSession], _: ReadLimited
) -> AdaptationOut:
    adaptation = await repository.get(session, adaptation_id)
    if adaptation is None:
        raise not_found(ADAPTATION_MISSING)
    return adaptation


@admin.get("/adaptations")
async def list_adaptations(  # noqa: PLR0913
    *,
    _admin: AdminPerson,
    session: FromDishka[AsyncSession],
    innovation: SlugFilter = None,
    institution_type: InstitutionType | None = None,
    powiat: PowiatFilter = None,
    page: PageNumber = 1,
    per_page: PerPage = 20,
) -> Page[AdminAdaptation]:
    return await repository.list_admin(
        session,
        innovation=innovation,
        institution_type=institution_type,
        powiat=powiat,
        page=page,
        per_page=per_page,
    )
