from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import ApiError, invalid
from services.ai import AiBudgetExceededError, AiUnavailableError
from services.needs import TextRejectedError
from utils.db.models.category import Category

AI_UNAVAILABLE = ApiError(
    503,
    "ai_unavailable",
    "Wyszukiwanie jest chwilowo niedostępne. Spróbuj ponownie za kilka minut.",
)
CONSENT_MISSING = invalid(
    "contact_consent", "Zaznacz zgodę na kontakt, jeśli podajesz adres e-mail."
)


async def categories_by_slug(session: AsyncSession) -> dict[str, Category]:
    return {c.slug: c for c in (await session.exec(select(Category))).all()}


def translate(error: Exception) -> ApiError:
    if isinstance(error, TextRejectedError):
        return ApiError(
            422,
            error.code,
            error.message,
            fields=[{"field": "text", "message": error.message}],
        )
    if isinstance(error, (AiUnavailableError, AiBudgetExceededError)):
        return AI_UNAVAILABLE
    raise error
