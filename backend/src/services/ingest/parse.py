import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from urllib.parse import urljoin

from selectolax.parser import HTMLParser, Node

from .authors import organizations

BASE_URL = "https://rops.krakow.pl"
LIBRARY_PATH = "/innowacje-spoleczne/biblioteka-innowacji-spolecznych"
CATEGORIES_URL = f"{BASE_URL}{LIBRARY_PATH}/kategorie"
TERMS_URL = (
    f"{BASE_URL}/mpliki/IS/BIBLIOTEKA_INNOWACJI_SPOECZNYCH/"
    "Zasady_wykorzystania_innowacji_MIIS.pdf"
)

CATEGORY_LINK = re.compile(re.escape(LIBRARY_PATH) + r"/(?P<slug>dla-[a-z0-9-]+)/?$")
ITEM_LINK = re.compile(
    re.escape(LIBRARY_PATH) + r"/(?P<category>[a-z0-9-]+),(?P<slug>[a-z0-9-]+)/?$"
)

SECTION_KEYS = (
    ("na czym polega", "what_it_is"),
    ("jakich problem", "problems"),
    ("grupa docelowa", "target_group"),
    ("kto może skorzystać", "who_can_use"),
    ("czy to działa", "effectiveness"),
    ("autor", "authors"),
)
SECTION_ORDER = [key for _, key in SECTION_KEYS]
SECTION_HEADING = re.compile(
    r"^\d\.\s*(" + "|".join(re.escape(marker) for marker, _ in SECTION_KEYS) + ")",
    re.IGNORECASE,
)
BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)


@dataclass(slots=True)
class CategoryLink:
    slug: str
    name: str
    url: str
    position: int


@dataclass(slots=True)
class ItemLink:
    slug: str
    category_slug: str
    url: str
    lead: str


@dataclass(slots=True)
class CategoryPage:
    name: str
    items: list[ItemLink]


@dataclass(slots=True)
class ScrapedInnovation:
    slug: str
    category_slug: str
    source_url: str
    title: str
    lead: str = ""
    what_it_is: str = ""
    problems: str = ""
    target_group: str = ""
    who_can_use: str = ""
    effectiveness: str | None = None
    authors: list[str] = field(default_factory=list)
    qr_url: str | None = None
    video_url: str | None = None
    materials_url: str | None = None
    brochure_url: str | None = None
    license: str | None = None
    category_icon_url: str | None = None

    def content(self) -> dict[str, object]:
        data = asdict(self)
        data.pop("category_icon_url")
        return data

    def content_hash(self) -> str:
        payload = json.dumps(self.content(), ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ").replace("\u200b", "")).strip()


def absolute(href: str | None) -> str | None:
    if not href:
        return None
    return urljoin(BASE_URL + "/", href.strip())


def _main(tree: HTMLParser) -> Node | None:
    return tree.css_first(".content__main") or tree.css_first("main")


def parse_categories(html: str) -> list[CategoryLink]:
    tree = HTMLParser(html)
    main = _main(tree)
    if main is None:
        return []
    seen: dict[str, CategoryLink] = {}
    for link in main.css("a[href]"):
        href = absolute(link.attributes.get("href")) or ""
        match = CATEGORY_LINK.search(href)
        if not match or match["slug"] in seen:
            continue
        name = squash(link.text())
        name = re.sub(r"^innowacje\s+", "", name, flags=re.IGNORECASE)
        seen[match["slug"]] = CategoryLink(
            slug=match["slug"],
            name=name[:1].upper() + name[1:],
            url=f"{BASE_URL}{LIBRARY_PATH}/{match['slug']}",
            position=len(seen),
        )
    return list(seen.values())


def _lead(entry: Node) -> str:
    for paragraph in entry.css("p"):
        if paragraph.css_first("a, table, strong"):
            continue
        text = squash(paragraph.text())
        if text and not text.isupper():
            return text
    return ""


def parse_category(html: str) -> CategoryPage:
    tree = HTMLParser(html)
    main = _main(tree)
    title = main.css_first("h2.page-title") if main else None
    items: dict[str, ItemLink] = {}
    if main is not None:
        for entry in main.css(".news-list__item"):
            link = entry.css_first("a.news-list__title")
            href = absolute(link.attributes.get("href") if link else None) or ""
            match = ITEM_LINK.search(href)
            if not match or match["slug"] in items:
                continue
            items[match["slug"]] = ItemLink(
                slug=match["slug"],
                category_slug=match["category"],
                url=href,
                lead=_lead(entry),
            )
    return CategoryPage(
        name=squash(title.text()) if title else "", items=list(items.values())
    )


def _paragraph(node: Node) -> str:
    lines = (squash(line) for line in node.text().split("\n"))
    return "\n".join(line for line in lines if line and not SECTION_HEADING.match(line))


def _block_text(nodes: list[Node]) -> str:
    blocks: list[str] = []
    for node in nodes:
        if node.tag in {"ul", "ol"}:
            items = [squash(li.text()) for li in node.css("li")]
            blocks.append("\n".join(f"- {item}" for item in items if item))
        else:
            blocks.append(_paragraph(node))
    return "\n\n".join(block for block in blocks if block)


def _lines(nodes: list[Node]) -> list[str]:
    lines: list[str] = []
    for node in nodes:
        lines.extend(
            line for line in node.text(separator="\n").split("\n") if line.strip()
        )
    return lines


def _section_key(heading: str, index: int) -> str | None:
    lowered = re.sub(r"^\d+\.\s*", "", heading.lower()).strip()
    for marker, key in SECTION_KEYS:
        if marker in lowered:
            return key
    if not lowered and index < len(SECTION_ORDER):
        return SECTION_ORDER[index]
    return None


def _apply_link(item: ScrapedInnovation, href: str, icon: str) -> None:
    if "youtube.com" in href or "youtu.be" in href or "play" in icon:
        item.video_url = item.video_url or href
    elif "read2" in icon:
        item.materials_url = item.materials_url or href
    elif "lupa" in icon:
        item.brochure_url = item.brochure_url or href
    elif "creativecommons.org/licenses/by/4.0" in href:
        item.license = "CC BY 4.0"
    elif "symbol-c" in icon:
        item.license = "Zasady wykorzystania ROPS"


def _apply_image(item: ScrapedInnovation, src: str) -> None:
    if "BIBLIOTEKA_INNOWACJI_SPOECZNYCH" in src and src.lower().endswith(".png"):
        item.qr_url = absolute(src)
    elif "iKONY_na_www" in src and item.category_icon_url is None:
        name = src.rsplit("/", 1)[-1]
        if not name.startswith(("read", "lupa", "play", "CC_", "symbol")):
            item.category_icon_url = absolute(src)


def _apply_toolbar(item: ScrapedInnovation, content: Node) -> None:
    for link in content.css("table a[href]"):
        href = absolute(link.attributes.get("href"))
        img = link.css_first("img")
        if href:
            _apply_link(item, href, (img.attributes.get("src") or "") if img else "")
    for img in content.css("table img[src]"):
        _apply_image(item, img.attributes.get("src") or "")


def parse_item(html: str, link: ItemLink) -> ScrapedInnovation:
    tree = HTMLParser(BREAK.sub("\n", html))
    main = _main(tree)
    if main is None:
        msg = f"no main content at {link.url}"
        raise ValueError(msg)
    title = main.css_first("h2.page-title")
    item = ScrapedInnovation(
        slug=link.slug,
        category_slug=link.category_slug,
        source_url=link.url,
        title=squash(title.text()) if title else link.slug,
        lead=link.lead,
    )
    content = main.css_first(".text-content")
    if content is None:
        return item
    _apply_toolbar(item, content)

    sections: list[tuple[str, list[Node]]] = []
    for child in content.iter():
        if child.tag in {"h3", "h4", "h5"}:
            sections.append((squash(child.text()), []))
        elif sections and child.tag != "table":
            sections[-1][1].append(child)

    for index, (heading, nodes) in enumerate(sections):
        key = _section_key(heading, index)
        if key == "authors":
            item.authors = organizations(_lines(nodes))
        elif key == "effectiveness":
            item.effectiveness = _block_text(nodes) or None
        elif key is not None:
            setattr(item, key, _block_text(nodes))
    return item
