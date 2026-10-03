from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import invalid
from services.dialogue import contacts
from services.dialogue.schemas import ContactProfile
from services.modules import normalize_email

router = APIRouter(route_class=DishkaRoute)
EMAIL_FIELD = "email"
EMAIL_MESSAGE = "Wpisz poprawny adres e-mail."


@router.get("/contact-profile")
async def contact_profile(
    email: Annotated[str, Query(min_length=3, max_length=254)],
    session: FromDishka[AsyncSession],
) -> ContactProfile:
    normalized = normalize_email(email)
    if normalized is None:
        raise invalid(EMAIL_FIELD, EMAIL_MESSAGE)
    return await contacts.profile(session, normalized)
