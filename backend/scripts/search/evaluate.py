import argparse
import asyncio
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dependencies.container import container
from services.needs import search_need
from services.search import cached_query_embedding, hybrid_search
from utils.db import init_db, session_scope

console = Console()
NOTHING = "nothing"
CANDIDATES = 12
HTTP_PAUSE = 7.0
HTTP_RETRIES = 3


@dataclass(frozen=True, slots=True)
class Case:
    text: str
    expect: tuple[str, ...]
    nothing_ok: bool = False


CASES = (
    Case("mam depresję", ("centrum-antydepresyjne",)),
    Case(
        "od miesięcy jestem przygnębiony i nic mi się nie chce",
        ("centrum-antydepresyjne",),
    ),
    Case("nie mam z kim zostawić mamy z demencją", (), nothing_ok=True),
    Case("mama ma demencję i gubi się na spacerach", ("kody-qr-na-pomoc-seniorom",)),
    Case(
        "tata ma alzheimera i wszystko zapomina",
        (
            "kody-qr-na-pomoc-seniorom",
            "korytarz-wspomnien",
            "sciezka-treningu-umyslu",
            "bawita",
        ),
    ),
    Case(
        "jestem sama, nikt mnie nie odwiedza",
        (
            "mobilne-centrum-pomocy-dla-osob-starszych",
            "terapeuta-przestrzeni",
            "wirtualne-izby-pamieci",
        ),
        nothing_ok=True,
    ),
    Case(
        "moje dziecko jest niepełnosprawne i nie daję już rady",
        (
            "uwaznione-rodzienstwo",
            "to-nie-koniec-swiata-to-poczatek-swiata",
            "nasz-wspolny-rodzinny-swiat-poznaje-ucze-reaguje",
            "osa-i-eco-puzzle",
        ),
    ),
    Case(
        "syn ma autyzm i nie mówi",
        ("jezykolamacz", "piosenki-uczestniczace", "autyzm-i-ja"),
    ),
    Case(
        "nie mam czym dojechać do lekarza, autobus nie jeździ",
        ("mobilne-centrum-pomocy-dla-osob-starszych",),
        nothing_ok=True,
    ),
    Case(
        "mąż pije i w domu są awantury",
        ("mobilna-pomoc-terapeutyczna",),
        nothing_ok=True,
    ),
    Case("przemoc w rodzinie", ("mobilna-pomoc-terapeutyczna",)),
    Case(
        "straciłem mieszkanie i śpię na dworcu",
        (
            "szlakiem-ludzi-bezdomnych",
            "wiejski-program-pomocy-osobom-w-kryzysie-bezdomnosci-sciezka-feniksa",
        ),
    ),
    Case(
        "mam 55 lat i straciłem pracę",
        ("agencja-pracy-incydentalnej", "mobilna-gielda-pracy"),
        nothing_ok=True,
    ),
    Case(
        "jestem z Ukrainy i nie znam polskiego",
        (
            "osoby-niewidome-i-niedowidzace-jako-nauczyciele-jezyka-polskiego",
            "health-guide-pl",
            "zrozum-moja-kulture-zrozum-mnie",
        ),
    ),
    Case(
        "słabo słyszę i nie mogę się dogadać w urzędzie",
        (
            "dostepny-wniosek-dla-ggluchych",
            "wielodziedzinowy-slownik-terminow-specjalistycznych-pl-pjm",
            "straznik",
        ),
    ),
    Case(
        "babcia przewróciła się w łazience",
        ("obu-obuwie-po-domu", "przenosne-modularne-lazienki", "terapeuta-przestrzeni"),
    ),
    Case("nie widzę i nie mogę sam zrobić zakupów", ("czytamoda", "zakupy-bez-barier")),
    Case(
        "córka ma myśli samobójcze", ("bez-presji-z-depresji", "centrum-antydepresyjne")
    ),
    Case(
        "tata wyszedł ze szpitala i nikt się nim w domu nie zajmuje",
        ("organizator-kompleksowej-opieki-w-miejscu-zamieszkania",),
    ),
    Case(
        "mama nie umie obsłużyć biletomatu ani bankomatu",
        ("merkury", "wirtualne-izby-pamieci"),
    ),
    Case(
        "nie wiem jak załatwić sprawy spadkowe po mężu",
        (
            "stworzenie-narzedzia-ulatwiajacego-seniorom-prawidlowe-regulowanie-spraw-spadkowych",
        ),
    ),
    Case("mam raka i boję się leczenia", ("oncotriada",)),
    Case("zapominam brać leki", ("inteligentny-organizer-do-lekow",)),
    Case("asdf qwer zxcv", ()),
    Case("jaka będzie jutro pogoda w Krakowie", ()),
    Case("kocham pierogi z kapustą", ()),
)


@dataclass(slots=True)
class Row:
    case: Case
    rank: int | None
    slugs: list[str]
    reason: str | None
    first_reason: str


def verdict(row: Row) -> bool:
    found = any(slug in row.case.expect for slug in row.slugs)
    if not row.slugs:
        return not row.case.expect or row.case.nothing_ok
    if not row.case.expect:
        return False
    return found


async def retrieval_rank(text: str, expect: tuple[str, ...]) -> int | None:
    vector = await cached_query_embedding(text, kind="embed_eval")
    async with session_scope() as session:
        hits = await hybrid_search(session, text, vector, limit=CANDIDATES)
    for rank, hit in enumerate(hits, start=1):
        if hit.innovation.slug in expect:
            return rank
    return None


async def local_row(case: Case, *, reasons: bool) -> Row:
    rank = await retrieval_rank(case.text, case.expect) if case.expect else None
    if not reasons:
        return Row(case, rank, [], None, "")
    async with session_scope() as session:
        outcome = await search_need(session, case.text)
    slugs = [r.hit.innovation.slug for r in outcome.results]
    first = outcome.results[0].reason if outcome.results else ""
    return Row(case, rank, slugs, outcome.reason, first)


def post_match(url: str, text: str) -> dict:
    request = urllib.request.Request(  # noqa: S310
        f"{url.rstrip('/')}/api/match",
        data=json.dumps({"text": text}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "hubmi-search-eval"},
        method="POST",
    )
    for _ in range(HTTP_RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
                return json.load(response)
        except urllib.error.HTTPError as e:
            if e.code != 429:  # noqa: PLR2004
                raise
            time.sleep(int(e.headers.get("Retry-After") or 30) + 1)
    message = "rate limited three times in a row"
    raise RuntimeError(message)


def http_row(case: Case, url: str) -> Row:
    body = post_match(url, case.text)
    results = body.get("results") or []
    slugs = [item["innovation"]["slug"] for item in results]
    first = results[0]["reason"] if results else ""
    return Row(case, None, slugs, body.get("reason"), first)


def show(rows: list[Row], *, title: str, final: bool) -> None:
    table = Table(title=title, show_lines=True)
    table.add_column("#", justify="right")
    table.add_column("text")
    table.add_column("expected")
    if not final:
        table.add_column("rank in candidates", justify="right")
    else:
        table.add_column("results")
        table.add_column("first reason")
        table.add_column("ok")
    passed = 0
    for i, row in enumerate(rows, start=1):
        expected = ", ".join(row.case.expect) or NOTHING
        if row.case.nothing_ok and row.case.expect:
            expected += f" or {NOTHING}"
        if not final:
            ok = row.rank is not None or not row.case.expect
            passed += ok
            table.add_row(str(i), row.case.text, expected, str(row.rank or "-"))
            continue
        ok = verdict(row)
        passed += ok
        results = ", ".join(row.slugs) or f"{NOTHING} ({row.reason})"
        table.add_row(
            str(i),
            row.case.text,
            expected,
            results,
            row.first_reason,
            "yes" if ok else "NO",
        )
    console.print(table)
    console.print(f"[bold]{passed}/{len(rows)}[/] pass")


async def run_local(args: argparse.Namespace) -> list[Row]:
    await init_db()
    try:
        return [
            await local_row(case, reasons=args.reasons) for case in CASES[: args.limit]
        ]
    finally:
        await container.close()


def run_http(args: argparse.Namespace) -> list[Row]:
    rows = []
    for i, case in enumerate(CASES[: args.limit]):
        if i:
            time.sleep(HTTP_PAUSE)
        rows.append(http_row(case, args.url))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate search on plain resident phrases"
    )
    parser.add_argument("--url", help="run against a live site through POST /api/match")
    parser.add_argument(
        "--reasons",
        action="store_true",
        help="local: also run the reason model, one call per phrase",
    )
    parser.add_argument("--limit", type=int, default=len(CASES))
    args = parser.parse_args()
    if args.url:
        rows = run_http(args)
        show(rows, title=f"POST {args.url}/api/match", final=True)
        return
    rows = asyncio.run(run_local(args))
    show(rows, title="local", final=args.reasons)
    if args.reasons:
        ranks = [r for r in rows if r.case.expect]
        found = sum(r.rank is not None for r in ranks)
        console.print(
            f"retrieval: expected item among {CANDIDATES} candidates "
            f"for {found}/{len(ranks)}"
        )


if __name__ == "__main__":
    main()
