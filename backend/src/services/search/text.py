import re
import unicodedata

STOPWORDS = frozenset(
    [
        "ale",
        "albo",
        "ani",
        "aby",
        "bardzo",
        "bez",
        "bo",
        "by",
        "byc",
        "byl",
        "byla",
        "byli",
        "bylo",
        "czy",
        "dla",
        "do",
        "gdy",
        "gdzie",
        "go",
        "ich",
        "ja",
        "jak",
        "jaki",
        "jakie",
        "jest",
        "jestem",
        "jej",
        "jego",
        "juz",
        "ktora",
        "ktore",
        "ktory",
        "ktorzy",
        "kiedy",
        "lub",
        "ma",
        "mam",
        "mamy",
        "mi",
        "mnie",
        "moja",
        "moje",
        "moj",
        "moze",
        "mozna",
        "na",
        "nad",
        "nam",
        "nas",
        "nasz",
        "nasza",
        "nasze",
        "nie",
        "niej",
        "nim",
        "nic",
        "o",
        "od",
        "oraz",
        "po",
        "pod",
        "przez",
        "przy",
        "sa",
        "sie",
        "sobie",
        "ta",
        "tak",
        "tam",
        "te",
        "tego",
        "tej",
        "ten",
        "to",
        "tu",
        "tym",
        "u",
        "w",
        "we",
        "z",
        "za",
        "ze",
        "co",
        "coz",
        "jako",
        "takze",
        "tez",
        "wiec",
        "mojej",
        "mojego",
        "mojemu",
        "naszej",
        "naszego",
        "bardzo",
        "chce",
        "chcemy",
        "potrzebuje",
        "potrzebujemy",
        "prosze",
        "pomoc",
        "pomocy",
        "problem",
        "problemu",
        "problemem",
    ]
)
WORD = re.compile(r"[a-z0-9]+")
MIN_WORD = 3
STEM_FROM = 6
MAX_TERMS = 24


def fold(text: str) -> str:
    text = text.lower().replace("ł", "l")
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def stem(word: str) -> str:
    if len(word) < STEM_FROM:
        return word
    return word[: max(STEM_FROM - 1, len(word) - 3)]


def keyword_terms(text: str) -> list[str]:
    terms: list[str] = []
    for word in WORD.findall(fold(text)):
        if len(word) < MIN_WORD or word in STOPWORDS:
            continue
        term = f"{stem(word)}:*" if len(word) > MIN_WORD else word
        if term not in terms:
            terms.append(term)
    return terms[:MAX_TERMS]


def keyword_query(text: str) -> str | None:
    terms = keyword_terms(text)
    return " | ".join(terms) if terms else None


def letters_ratio(text: str) -> float:
    stripped = [c for c in text if not c.isspace()]
    if not stripped:
        return 0.0
    return sum(c.isalpha() for c in stripped) / len(stripped)


def word_count(text: str) -> int:
    return len([w for w in WORD.findall(fold(text)) if len(w) >= MIN_WORD - 1])
