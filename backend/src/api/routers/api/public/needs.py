import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Header, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import not_found
from api.limits import rate_limit
from services.ai import AiBudgetExceededError, AiUnavailableError
from services.needs import (
    NeedNotFoundError,
    TextRejectedError,
    create_need,
    update_need,
)

from .common import CONSENT_MISSING, translate
from .schemas import ClusterRef, NeedIn, NeedOut, NeedPatch, NeedPatched

router = APIRouter(route_class=DishkaRoute)
create_limiter = rate_limit("needs", per_minute=5, per_day=30)
patch_limiter = rate_limit("needs_patch", per_minute=10)


@router.post(
    "", status_code=status.HTTP_201_CREATED, dependencies=[Depends(create_limiter)]
)
async def create(body: NeedIn, session: FromDishka[AsyncSession]) -> NeedOut:
    if body.contact_email and not body.contact_consent:
        raise CONSENT_MISSING
    try:
        outcome = await create_need(
            session,
            body.text,
            powiat=body.powiat,
            contact_email=body.contact_email,
            shown_innovation_slugs=body.shown_innovation_slugs,
        )
    except (TextRejectedError, AiUnavailableError, AiBudgetExceededError) as e:
        raise translate(e) from e
    cluster = outcome.cluster
    return NeedOut(
        id=outcome.need.id,
        number=outcome.need.number or 0,
        edit_token=outcome.token,
        similar_count=outcome.similar_count,
        cluster=ClusterRef(id=cluster.id, title=cluster.title, size=cluster.size)
        if cluster
        else None,
    )


@router.patch("/{need_id}", dependencies=[Depends(patch_limiter)])
async def patch(
    need_id: uuid.UUID,
    body: NeedPatch,
    session: FromDishka[AsyncSession],
    token: Annotated[str | None, Header(alias="X-Need-Token")] = None,
) -> NeedPatched:
    if body.contact_email and not body.contact_consent:
        raise CONSENT_MISSING
    try:
        fields = body.model_fields_set
        need = await update_need(
            session,
            need_id,
            token,
            powiat=body.powiat,
            contact_email=body.contact_email,
            contact_email_provided="contact_email" in fields,
            contact_consent=body.contact_consent
            if "contact_consent" in fields
            else None,
            nothing_fits=body.nothing_fits,
        )
    except NeedNotFoundError as e:
        raise not_found() from e
    return NeedPatched(id=need.id, status=need.status.value)
