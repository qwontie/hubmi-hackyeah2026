import re

from services.signing import signed_key

MIN_TEXT = 10
MAX_TEXT = 2000
MIN_WORDS = 2
MAX_LINKS = 2
TITLE_WORDS = 8
TITLE_CHARS = 60
SPAM = "spam_rejected"
TOO_SHORT = "text_too_short"
TOO_LONG = "text_too_long"
TOO_FEW_WORDS = "too_few_words"
TOO_MANY_LINKS = "too_many_links"
WORD = re.compile(r"[^\W\d_]{2,}")
LINK = re.compile(r"https?://|www\.", re.IGNORECASE)
MESSAGES = {
    SPAM: "Nie udało się przyjąć zgłoszenia. Odśwież stronę i spróbuj ponownie.",
    TOO_SHORT: f"Opis musi mieć co najmniej {MIN_TEXT} znaków.",
    TOO_LONG: f"Opis może mieć najwyżej {MAX_TEXT} znaków.",
    TOO_FEW_WORDS: "Opisz problem w co najmniej dwóch słowach.",
    TOO_MANY_LINKS: f"Opis może zawierać najwyżej {MAX_LINKS} linki.",
}


class TextRejectedError(ValueError):
    def __init__(self, code: str, message: str, field: str = "text") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field


def rejected(code: str, field: str = "text") -> TextRejectedError:
    return TextRejectedError(code, MESSAGES[code], field)


def collapse(text: str) -> str:
    return " ".join(text.split())


def intake_text(text: str, *, honeypot: str | None = None) -> str:
    if honeypot and honeypot.strip():
        raise rejected(SPAM, "website")
    text = collapse(text)
    if len(text) < MIN_TEXT:
        raise rejected(TOO_SHORT)
    if len(text) > MAX_TEXT:
        raise rejected(TOO_LONG)
    if len(WORD.findall(text)) < MIN_WORDS:
        raise rejected(TOO_FEW_WORDS)
    if len(LINK.findall(text)) > MAX_LINKS:
        raise rejected(TOO_MANY_LINKS)
    return text


def first_words(text: str) -> str:
    words = collapse(text).split(" ")[:TITLE_WORDS]
    title = " ".join(words)
    if len(title) > TITLE_CHARS:
        title = title[:TITLE_CHARS].rsplit(" ", 1)[0] or title[:TITLE_CHARS]
    return title.rstrip(".,;:!?-") + ("…" if title != collapse(text) else "")


def dedupe_key(client: str, text: str) -> str:
    return signed_key("need-dedupe", client, collapse(text).casefold())
