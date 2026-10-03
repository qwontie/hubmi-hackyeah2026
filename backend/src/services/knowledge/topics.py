TOPICS: dict[str, str] = {
    "seniorzy": "Seniorzy",
    "rodzina-i-dzieci": "Rodzina i dzieci",
    "piecza-zastepcza": "Piecza zastępcza",
    "niepelnosprawnosc": "Niepełnosprawność",
    "bezdomnosc": "Bezdomność",
    "ubostwo": "Ubóstwo",
    "cudzoziemcy": "Cudzoziemcy",
    "zdrowie": "Zdrowie",
    "zdrowie-psychiczne": "Zdrowie psychiczne",
    "przemoc-domowa": "Przemoc domowa",
    "uzaleznienia": "Uzależnienia",
    "rynek-pracy": "Praca i aktywizacja",
    "ekonomia-spoleczna": "Ekonomia społeczna",
    "mieszkalnictwo": "Mieszkalnictwo",
    "uslugi-spoleczne": "Usługi społeczne",
    "innowacje-spoleczne": "Innowacje społeczne",
    "organizacje-i-wolontariat": "Organizacje i wolontariat",
    "kadry-pomocy-spolecznej": "Kadry pomocy społecznej",
    "badania-i-ewaluacja": "Badania i ewaluacja",
}

AREAS: dict[str, str] = {
    "rodzina-i-piecza": "Rodzina i piecza zastępcza",
    "bezdomnosc": "Bezdomność",
    "niepelnosprawnosc": "Niepełnosprawność",
    "ubostwo": "Ubóstwo",
    "cudzoziemcy": "Integracja cudzoziemców",
    "zdrowie": "Zdrowie",
    "zdrowie-psychiczne": "Zdrowie psychiczne",
    "seniorzy": "Seniorzy",
}

KIND_NAMES: dict[str, str] = {
    "report": "Raport",
    "publication": "Publikacja",
    "guide": "Poradnik",
    "video": "Film",
}


def topic_ref(slug: str) -> dict[str, str]:
    return {"slug": slug, "name": TOPICS.get(slug, slug)}


def area_ref(slug: str) -> dict[str, str]:
    return {"slug": slug, "name": AREAS.get(slug, slug)}


def clean_topics(values: list[str], limit: int = 4) -> list[str]:
    seen: list[str] = []
    for value in values:
        slug = value.strip().lower()
        if slug in TOPICS and slug not in seen:
            seen.append(slug)
    return seen[:limit]


DASHES = str.maketrans({0x2014: "-", 0x2013: "-"})
