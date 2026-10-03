from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import invalid
from services.dialogue import contacts
from services.dialogue.schemas import ContactProfile, ContactProfileRequest
from services.modules import normalize_email

router = APIRouter(route_class=DishkaRoute)
EMAIL_FIELD = "email"
EMAIL_MESSAGE = "Wpisz poprawny adres e-mail."


@router.post("/contact-profile")
async def contact_profile(
    body: ContactProfileRequest, session: FromDishka[AsyncSession]
) -> ContactProfile:
    normalized = normalize_email(body.email)
    if normalized is None:
        raise invalid(EMAIL_FIELD, EMAIL_MESSAGE)
    return await contacts.profile(session, normalized.lower())
