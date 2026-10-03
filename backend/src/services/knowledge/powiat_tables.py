import re
import unicodedata
from dataclasses import dataclass

from services.needs import POWIATS

TABLE_TITLE = re.compile(
    r"Tabela\s+\d+\.\s+(?P<title>.+?)(?=\n(?:powiat|m\.|Powiat|Wyszczególnienie)\b)",
    re.DOTALL,
)
ROW = re.compile(
    r"^(?P<name>(?:powiat|m\.)\s+[^\d\n]+?)\s+"
    r"(?P<value>\d{1,3}(?:[ \u00a0]\d{3})*(?:,\d+)?)\s*(?P<unit>%?)\s*$",
    re.MULTILINE,
)
REGION_ROW = re.compile(
    r"^Województwo małopolskie\s+"
    r"(?P<value>\d{1,3}(?:[ \u00a0]\d{3})*(?:,\d+)?)\s*%?\s*$",
    re.MULTILINE,
)
YEAR = re.compile(r"\b(20\d{2})\s*r\.?")
REGION = "wojewodztwo-malopolskie"
MIN_POWIATS = 20
LABEL_TAIL = re.compile(
    r"\s+w\s+powiatach(?:\s+województwa\s+małopolskiego)?(?:\s+w\s+20\d{2}\s*r)?\.?$",
    re.IGNORECASE,
)
CITY_PREFIX = "m. "


@dataclass(frozen=True, slots=True)
class PowiatValue:
    powiat: str
    value: float
    raw: str


@dataclass(frozen=True, slots=True)
class PowiatTable:
    key: str
    title: str
    unit: str
    year: int | None
    page: int
    values: list[PowiatValue]


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.replace("ł", "l").replace("Ł", "L"))
    return " ".join(text.encode("ascii", "ignore").decode().lower().split())


NAME_TO_SLUG = {_fold(name): slug for slug, name in POWIATS.items()}


def powiat_slug(name: str) -> str | None:
    name = name.strip()
    name = name.removeprefix(CITY_PREFIX)
    return NAME_TO_SLUG.get(_fold(name))


def _key(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", _fold(title)).strip("-")
    return slug[:80].rstrip("-")


def clean_title(title: str) -> str:
    return LABEL_TAIL.sub("", title.rstrip(".")).strip()


def _number(raw: str) -> float:
    return float(raw.replace(" ", "").replace(" ", "").replace(",", "."))


def parse_page(page: str, number: int) -> list[PowiatTable]:
    tables: list[PowiatTable] = []
    for match in TABLE_TITLE.finditer(page):
        title = " ".join(match.group("title").split())
        block = page[match.end() : match.end() + 2500]
        values: dict[str, PowiatValue] = {}
        units: set[str] = set()
        for row in ROW.finditer(block):
            slug = powiat_slug(row.group("name"))
            if slug is None or slug in values:
                continue
            values[slug] = PowiatValue(
                powiat=slug, value=_number(row.group("value")), raw=row.group(0).strip()
            )
            units.add(row.group("unit"))
        if len(values) < MIN_POWIATS:
            continue
        region = REGION_ROW.search(block)
        if region:
            values[REGION] = PowiatValue(
                powiat=REGION,
                value=_number(region.group("value")),
                raw=region.group(0).strip(),
            )
        year = YEAR.search(title)
        tables.append(
            PowiatTable(
                key=_key(clean_title(title)),
                title=title.rstrip("."),
                unit="%" if units == {"%"} else "",
                year=int(year.group(1)) if year else None,
                page=number,
                values=list(values.values()),
            )
        )
    return tables


def parse_tables(pages: list[str]) -> list[PowiatTable]:
    found: list[PowiatTable] = []
    for number, page in enumerate(pages, start=1):
        found.extend(parse_page(page, number))
    return found
