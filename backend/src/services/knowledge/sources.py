import re
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urljoin

from selectolax.parser import HTMLParser, Node

from utils.db.models.material import MaterialKind

BASE_URL = "https://rops.krakow.pl"
REPORTS_URL = f"{BASE_URL}/badania-analizy-raporty/raporty-z-badan"
ASSESSMENT_URL = (
    f"{BASE_URL}/badania-analizy-raporty/"
    "ocena-zasobow-pomocy-spolecznej-w-woj-malopolskim/biezaca-ocena"
)
PUBLICATIONS_URL = f"{BASE_URL}/innowacje-spoleczne/publikacje-ze-swiata-innowacji"
GUIDES_URL = f"{BASE_URL}/dla-kadr-pomocy-spolecznej/poradniki"
MAP_OF_CHALLENGES_URL = (
    f"{BASE_URL}/mpliki/IS/IWS_20/za._nr_2._Mapa_Wyzwa_Spoecznych.pdf"
)
MAP_OF_CHALLENGES_TITLE = "Mapa Wyzwań Społecznych"
ASSESSMENT_TITLE = "Ocena zasobów pomocy społecznej województwa małopolskiego"
ASSESSMENT_SECTION = "Ocena zasobów pomocy społecznej"
TEXT_VERSION = "(wersja tekstowa)"

YEAR_PREFIX = re.compile(r"^\s*((?:19|20)\d{2})(?:\s*\|\s*|\s+I\s+)(.+)$", re.DOTALL)
YEAR_ANY = re.compile(r"\b((?:19|20)\d{2})\b")
PUBLICATION_YEAR = re.compile(r"rok wydania:\s*((?:19|20)\d{2})", re.IGNORECASE)
REPORT_YEAR = re.compile(r"Raport za\s+((?:19|20)\d{2})", re.IGNORECASE)
TEXT_ALTERNATIVE = re.compile(r"^Alternatywa tekstowa do\s*[„\"«]?(.+?)[”\"»]?\s*$")


@dataclass(frozen=True, slots=True)
class MaterialLink:
    file_url: str
    title: str
    kind: MaterialKind
    year: int | None
    source_url: str
    section: str


def _squash(text: str) -> str:
    return " ".join(text.split())


def _strip_quotes(text: str) -> str:
    return text.strip().strip('"„”«»').strip()


def _file_links(tree: HTMLParser) -> list[Node]:
    return tree.css("main a.files__link")


def _year_title(text: str) -> tuple[int | None, str]:
    text = _squash(text)
    match = YEAR_PREFIX.match(text)
    if match:
        return int(match.group(1)), _strip_quotes(match.group(2))
    return None, _strip_quotes(text)


def _listing(
    html: str, *, page_url: str, kind: MaterialKind, section: str
) -> list[MaterialLink]:
    links: list[MaterialLink] = []
    for node in _file_links(HTMLParser(html)):
        href = node.attributes.get("href")
        if not href:
            continue
        year, title = _year_title(node.text())
        if not title:
            continue
        links.append(
            MaterialLink(
                file_url=urljoin(page_url, href),
                title=title,
                kind=kind,
                year=year,
                source_url=page_url,
                section=section,
            )
        )
    return links


def parse_reports(html: str) -> list[MaterialLink]:
    return _listing(
        html, page_url=REPORTS_URL, kind=MaterialKind.REPORT, section="Raporty z badań"
    )


def parse_guides(html: str) -> list[MaterialLink]:
    return _listing(
        html, page_url=GUIDES_URL, kind=MaterialKind.GUIDE, section="Poradniki"
    )


def _assessment_title(text: str, year: int | None) -> str:
    text = _squash(text)
    alternative = TEXT_ALTERNATIVE.match(text)
    if alternative:
        inner = _strip_quotes(alternative.group(1))
        inner = inner.replace("OZPS WM", ASSESSMENT_TITLE)
        return f"{inner} {TEXT_VERSION}"
    if REPORT_YEAR.search(text) and year is not None:
        return f"{ASSESSMENT_TITLE} za {year} r."
    return text.rstrip(".")


def parse_assessment(html: str) -> list[MaterialLink]:
    tree = HTMLParser(html)
    main = tree.css_first("main")
    page_text = main.text(separator=" ") if main else ""
    year_match = re.search(r"Rok:\s*((?:19|20)\d{2})", page_text)
    page_year = int(year_match.group(1)) if year_match else None
    links: list[MaterialLink] = []
    for node in _file_links(tree):
        href = node.attributes.get("href")
        if not href:
            continue
        text = _squash(node.text())
        found = YEAR_ANY.search(text)
        year = int(found.group(1)) if found else page_year
        links.append(
            MaterialLink(
                file_url=urljoin(ASSESSMENT_URL, href),
                title=_assessment_title(text, year),
                kind=MaterialKind.REPORT,
                year=year,
                source_url=ASSESSMENT_URL,
                section=ASSESSMENT_SECTION,
            )
        )
    return links


def _publication_row(row: Node) -> MaterialLink | None:
    anchor = next(
        (
            a
            for a in row.css("a")
            if (a.attributes.get("href") or "").lower().endswith(".pdf")
        ),
        None,
    )
    strong = row.css_first("strong")
    if anchor is None or strong is None:
        return None
    text = row.text(separator=" ")
    if "Year of publication" in text:
        return None
    year = PUBLICATION_YEAR.search(text)
    return MaterialLink(
        file_url=urljoin(PUBLICATIONS_URL, anchor.attributes.get("href") or ""),
        title=_strip_quotes(_squash(strong.text())),
        kind=MaterialKind.PUBLICATION,
        year=int(year.group(1)) if year else None,
        source_url=PUBLICATIONS_URL,
        section="Publikacje ze świata innowacji",
    )


def parse_publications(html: str) -> list[MaterialLink]:
    tree = HTMLParser(html)
    links = [
        link
        for row in tree.css("main tr")
        if (link := _publication_row(row)) is not None
    ]
    links.extend(
        MaterialLink(
            file_url=link.file_url,
            title=link.title.title() if link.title.isupper() else link.title,
            kind=MaterialKind.GUIDE,
            year=link.year,
            source_url=PUBLICATIONS_URL,
            section="Publikacje ze świata innowacji",
        )
        for link in _listing(
            html,
            page_url=PUBLICATIONS_URL,
            kind=MaterialKind.GUIDE,
            section="Publikacje ze świata innowacji",
        )
    )
    return links


def map_of_challenges() -> MaterialLink:
    return MaterialLink(
        file_url=MAP_OF_CHALLENGES_URL,
        title=MAP_OF_CHALLENGES_TITLE,
        kind=MaterialKind.PUBLICATION,
        year=2024,
        source_url=MAP_OF_CHALLENGES_URL,
        section="Innowacje społeczne",
    )


Parser = Callable[[str], list[MaterialLink]]

LISTINGS: tuple[tuple[str, Parser], ...] = (
    (ASSESSMENT_URL, parse_assessment),
    (REPORTS_URL, parse_reports),
    (PUBLICATIONS_URL, parse_publications),
    (GUIDES_URL, parse_guides),
)


def dedupe(links: list[MaterialLink]) -> list[MaterialLink]:
    seen: dict[str, MaterialLink] = {}
    for link in links:
        seen.setdefault(link.file_url, link)
    return list(seen.values())
