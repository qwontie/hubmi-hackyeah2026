from services.modules import clean
from services.needs.intake import (
    LINK,
    MAX_LINKS,
    MIN_WORDS,
    SPAM,
    TOO_FEW_WORDS,
    TOO_LONG,
    TOO_MANY_LINKS,
    TOO_SHORT,
    WORD,
    TextRejectedError,
)
from services.needs.intake import MESSAGES as NEED_MESSAGES


def honeypot_check(honeypot: str | None) -> None:
    if honeypot and honeypot.strip():
        raise TextRejectedError(SPAM, NEED_MESSAGES[SPAM], "website")


def checked_text(
    field: str, value: str, *, minimum: int, maximum: int, words: int = MIN_WORDS
) -> str:
    text = clean(value)
    if len(text) < minimum:
        message = f"Napisz co najmniej {minimum} znaków."
        raise TextRejectedError(TOO_SHORT, message, field)
    if len(text) > maximum:
        message = f"Tekst może mieć najwyżej {maximum} znaków."
        raise TextRejectedError(TOO_LONG, message, field)
    if len(WORD.findall(text)) < words:
        message = "Napisz to zwykłymi słowami, w co najmniej dwóch wyrazach."
        raise TextRejectedError(TOO_FEW_WORDS, message, field)
    if len(LINK.findall(text)) > MAX_LINKS:
        message = f"Tekst może zawierać najwyżej {MAX_LINKS} linki."
        raise TextRejectedError(TOO_MANY_LINKS, message, field)
    return text
