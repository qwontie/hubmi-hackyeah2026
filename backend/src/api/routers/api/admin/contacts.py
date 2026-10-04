from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import invalid
from api.security import AdminPerson
from services.dialogue import contacts, erase
from services.dialogue.schemas import ContactProfile, ContactProfileRequest
from services.modules import normalize_email

router = APIRouter(route_class=DishkaRoute)
EMAIL_FIELD = "email"
EMAIL_MESSAGE = "Wpisz poprawny adres e-mail."


def address(body: ContactProfileRequest) -> str:
    normalized = normalize_email(body.email)
    if normalized is None:
        raise invalid(EMAIL_FIELD, EMAIL_MESSAGE)
    return normalized.lower()


@router.post("/contact-profile")
async def contact_profile(
    body: ContactProfileRequest, session: FromDishka[AsyncSession]
) -> ContactProfile:
    return await contacts.profile(session, address(body))


@router.post("/contacts/erase")
async def erase_contact(
    body: ContactProfileRequest, admin: AdminPerson, session: FromDishka[AsyncSession]
) -> erase.EraseResult:
    return await erase.erase(session, admin, address(body))
