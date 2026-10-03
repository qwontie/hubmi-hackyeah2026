import re
import unicodedata

SPACES = re.compile(r"[^\S\n]+")
BLANK_LINES = re.compile(r"\n{3,}")
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s.]+(\.[^@\s.]+)+$")
INVISIBLE = {"Cc", "Cf", "Co", "Cs"}
MIN_LETTERS = 3
MIN_DISTINCT_LETTERS = 3
MIN_WORDLIKE_SHARE = 0.5
EMAIL_MAX = 254


def clean(value: str) -> str:
    text = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    text = "".join(
        ch for ch in text if ch == "\n" or unicodedata.category(ch) not in INVISIBLE
    )
    lines = [SPACES.sub(" ", line).strip() for line in text.split("\n")]
    return BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def clean_line(value: str) -> str:
    return SPACES.sub(" ", clean(value).replace("\n", " ")).strip()


def is_meaningful(text: str) -> bool:
    letters = [ch.lower() for ch in text if ch.isalpha()]
    if len(letters) < MIN_LETTERS or len(set(letters)) < MIN_DISTINCT_LETTERS:
        return False
    visible = [ch for ch in text if not ch.isspace()]
    return len(letters) >= len(visible) * MIN_WORDLIKE_SHARE


def normalize_email(value: str) -> str | None:
    email = value.strip()
    if len(email) > EMAIL_MAX or not EMAIL.match(email):
        return None
    local, domain = email.rsplit("@", 1)
    return f"{local}@{domain.lower()}"
