from dataclasses import dataclass

from .schemas import GrantSection

ROPS_FORM_URL = (
    "https://rops.krakow.pl/mpliki/IS/IWS_20/za._3._Formularz_aplikacyjny_wzor.pdf"
)
ROPS_CALL_URL = (
    "https://rops.krakow.pl/nabory-szkolenia-granty-dotacje-wizyty-studyjne-"
    "studia-specjalizacje-superwizje/granty-na-innowacje-spoleczne"
)


@dataclass(frozen=True, slots=True)
class Template:
    slug: str
    title: str
    source_url: str
    description: str
    sections: tuple[GrantSection, ...]


def section(
    key: str, label: str, hint: str, max_length: int, *, required: bool = True
) -> GrantSection:
    return GrantSection(
        key=key, label=label, hint=hint, max_length=max_length, required=required
    )


ROPS_INNOVATION = Template(
    slug="rops-innowacje-spoleczne",
    title="Formularz aplikacyjny ROPS: pomysł na innowację społeczną",
    source_url=ROPS_FORM_URL,
    description=(
        "Pytania z formularza aplikacyjnego naboru pomysłów na innowacje "
        "społeczne ROPS w Krakowie (Inkubator Włączenia Społecznego 2.0, "
        "załącznik nr 3 do ogłoszenia). Dane pomysłodawcy i oświadczenia "
        "wypełnia się w formularzu ROPS, nie w HubMi."
    ),
    sections=(
        section(
            "title",
            "Tytuł innowacji",
            "Krótki tytuł, który kojarzy się z przedmiotem innowacji.",
            200,
        ),
        section(
            "description",
            "Opis innowacji",
            "Na czym polega innowacja? Jaki ma charakter: produkt, aplikacja, model "
            "pracy, rozwiązanie technologiczne? Jak wspiera włączenie społeczne "
            "i przeciwdziała wykluczeniu? Jak wpisuje się w ideę "
            "deinstytucjonalizacji?",
            4000,
        ),
        section(
            "novelty",
            "Innowacyjność rozwiązania",
            "Czy podobne rozwiązania są stosowane w Polsce albo na świecie? Jaką "
            "nową wartość wnosi pomysł? Czym wyróżnia się na tle innych?",
            3000,
        ),
        section(
            "diagnosis",
            "Diagnoza problemu",
            "Na jaki problem odpowiada innowacja? Jakie dane pokazują skalę "
            "problemu i na czym opiera się diagnoza (raporty, badania)? Czy "
            "problem jest zgodny z tematem z Mapy Wyzwań Społecznych?",
            3000,
        ),
        section(
            "recipients",
            "Opis odbiorców innowacji",
            "Do kogo jest skierowana innowacja? Co tę grupę wyróżnia, jakie ma "
            "potrzeby? Dlaczego te osoby są wykluczone lub zagrożone wykluczeniem?",
            3000,
        ),
        section(
            "change",
            "Zmiana, jaką wprowadza innowacja",
            "Jak rozwiązanie wpłynie na opisany problem? Co zmieni w życiu "
            "odbiorców i w ich włączeniu społecznym?",
            3000,
        ),
        section(
            "future",
            "Wizja przyszłości innowacji",
            "Czy innowację można zastosować na dużą skalę, dla innych grup, "
            "w innym miejscu? Jakie cechy na to pozwalają? Jak łatwo ją wdrożyć?",
            3000,
        ),
        section(
            "preparation",
            "Plan działania i koszty: okres przygotowawczy",
            "Co trzeba zrobić, żeby przystąpić do testu: co opracować, kogo "
            "zaangażować, kiedy i za ile? Ten okres trwa najwyżej 3 miesiące.",
            3000,
        ),
        section(
            "testing",
            "Plan działania i koszty: okres testowania",
            "Jak będzie przebiegał test, kogo zaangażować, ile osób przetestuje "
            "innowację, kiedy i za ile? Ten okres trwa najwyżej 9 miesięcy.",
            3000,
        ),
        section(
            "amount",
            "Wnioskowana kwota grantu",
            "Całkowita kwota grantu, zgodna z kosztami z planu działania.",
            500,
        ),
        section(
            "team",
            "Zespół projektowy i jego doświadczenie",
            "Kto odpowiada za zadania? Jakie doświadczenie w pracy z odbiorcami "
            "i we wdrażaniu innowacji społecznych mają te osoby lub organizacje?",
            3000,
        ),
    ),
)

TEMPLATES: dict[str, Template] = {ROPS_INNOVATION.slug: ROPS_INNOVATION}
