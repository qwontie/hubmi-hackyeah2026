from typing import Annotated

from fastapi import Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import ApiError, invalid, not_found
from api.limits import rate_limit
from services.modules import (
    MAX_PER_PAGE,
    clean,
    clean_line,
    is_meaningful,
    normalize_email,
    published_innovation,
)
from utils.db.models import Innovation

CONSENT_MESSAGE = "Zaznacz zgodę na kontakt, abyśmy mogli odpisać."
EMAIL_MESSAGE = "Wpisz poprawny adres e-mail."
UNCLEAR_MESSAGE = "Nie rozumiemy tego tekstu. Napisz kilka słów pełnymi zdaniami."
INNOVATION_MISSING = "Nie znaleziono takiej innowacji."

read_limit = rate_limit("modules_read", per_minute=120)

PageNumber = Annotated[int, Query(ge=1, le=10_000)]
PerPage = Annotated[int, Query(ge=1, le=MAX_PER_PAGE)]
ReadLimited = Annotated[None, Depends(read_limit)]


def unclear(field: str) -> ApiError:
    return ApiError(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "unclear_text",
        UNCLEAR_MESSAGE,
        fields=[{"field": field, "message": "Ten tekst wygląda na przypadkowe znaki."}],
    )


def required_text(field: str, value: str, *, minimum: int) -> str:
    text = clean(value)
    if len(text) < minimum:
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "text_too_short",
            f"Napisz co najmniej {minimum} znaków.",
            fields=[{"field": field, "message": "Za krótki tekst."}],
        )
    if not is_meaningful(text):
        raise unclear(field)
    return text


def optional_text(field: str, value: str | None, *, line: bool = False) -> str | None:
    if value is None:
        return None
    text = clean_line(value) if line else clean(value)
    if not text:
        return None
    if not is_meaningful(text):
        raise unclear(field)
    return text


def consented_email(email: str, consent: bool) -> str:  # noqa: FBT001
    if not consent:
        error = invalid("contact_consent", CONSENT_MESSAGE)
        raise error
    normalized = normalize_email(email)
    if normalized is None:
        error = invalid("contact_email", EMAIL_MESSAGE)
        raise error
    return normalized


def optional_email(email: str | None, consent: bool) -> str | None:  # noqa: FBT001
    if email is None or not email.strip():
        return None
    return consented_email(email, consent)


async def innovation_or_404(session: AsyncSession, slug: str) -> Innovation:
    innovation = await published_innovation(session, slug)
    if innovation is None:
        raise not_found(INNOVATION_MISSING)
    return innovation
