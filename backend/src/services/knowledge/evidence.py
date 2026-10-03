import re

from pydantic import BaseModel, Field

NUMBER = re.compile(r"\d(?:[\d\s.,]*\d)?")
DIGIT_GAP = re.compile(r"(?<=\d)[\s.](?=\d{3}\b)")
WORD = re.compile(r"\w+")
MIN_COVERAGE = 0.85
YEAR_ONLY = re.compile(r"\s*(?:19[5-9]\d|20[0-4]\d)\s*(?:r\.?|rok)?\s*")


class Figure(BaseModel):
    label: str = Field(
        description=(
            "what the number counts, plain Polish, max 12 words, exactly as the "
            "quote says it (a change stays a change, a share stays a share)"
        )
    )
    value: str = Field(description="the number exactly as written in the text")
    unit: str = Field(default="", description="unit if any: %, osób, rodzin, zł")
    year: int | None = Field(default=None, description="year the number refers to")
    quote: str = Field(description="exact text fragment containing the value")
    page: int = Field(description="page number of the quote")
    source_title: str = Field(
        default="", description="original source named in the text, if any"
    )


def normalize(text: str) -> str:
    text = text.replace("­", "").replace(" ", " ")
    text = text.translate(str.maketrans({"„": '"', "”": '"', "“": '"', "–": "-"}))
    text = DIGIT_GAP.sub("", text.lower())
    return " ".join(text.split())


def numeric_core(value: str) -> str | None:
    found = NUMBER.search(normalize(value))
    if found is None:
        return None
    return found.group(0).replace(" ", "")


def _coverage(quote: str, page: str) -> float:
    words = WORD.findall(quote)
    if not words:
        return 0.0
    present = set(WORD.findall(page))
    return sum(1 for word in words if word in present) / len(words)


def verify_figure(figure: Figure, page_text: str) -> bool:
    page = normalize(page_text)
    compact = page.replace(" ", "")
    core = numeric_core(figure.value)
    if core is None or core not in compact or YEAR_ONLY.fullmatch(figure.value):
        return False
    quote = normalize(figure.quote)
    if core not in quote.replace(" ", ""):
        return False
    return quote in page or _coverage(quote, page) >= MIN_COVERAGE
