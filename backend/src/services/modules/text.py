import re
import unicodedata

SPACES = re.compile(r"[^\S\n]+")
BLANK_LINES = re.compile(r"\n{3,}")
EMAIL = re.compile(
    r"^[^@\s\x00-\x1f\x7f]{1,64}@[^@\s.\x00-\x1f\x7f]+(\.[^@\s.\x00-\x1f\x7f]+)+$"
)
INVISIBLE = {"Cc", "Cf", "Co", "Cs"}
MIN_LETTERS = 3
MIN_DISTINCT_LETTERS = 3
MIN_WORDLIKE_SHARE = 0.5
EMAIL_MAX = 254
TOKEN = re.compile(r"[^\W\d_]+")
VOWELS = frozenset("aeiouyаеиоуыэюяіє")
DIGRAPH = re.compile(r"sz|cz|rz|ch|dz")
REPEATED_UNIT = re.compile(r"(.{1,3})\1{3,}")
SAME_THRICE = re.compile(r"(.)\1\1")
KEYBOARD_ROWS = ("asdfghjkl", "zxcvbnm", "qwe", "yuio")
MASH = frozenset(
    run[i : i + 3]
    for row in KEYBOARD_ROWS
    for run in (row, row[::-1])
    for i in range(len(run) - 2)
)
MIN_VOWEL_SHARE = 0.2
MAX_VOWEL_SHARE = 0.8
VOWEL_CHECK_FROM = 8
MIN_WORD = 3
MAX_CONSONANT_RUN = 5
MAX_VOWEL_RUN = 3
ACRONYM_MIN = 2
ACRONYM_MAX = 6


def clean(value: str) -> str:
    text = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    text = "".join(
        ch for ch in text if ch == "\n" or unicodedata.category(ch) not in INVISIBLE
    )
    lines = [SPACES.sub(" ", line).strip() for line in text.split("\n")]
    return BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def clean_line(value: str) -> str:
    return SPACES.sub(" ", clean(value).replace("\n", " ")).strip()


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower().replace("ł", "l"))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def longest_runs(word: str) -> tuple[int, int]:
    consonants = vowels = longest_consonants = longest_vowels = 0
    for ch in DIGRAPH.sub("c", word):
        if ch in VOWELS:
            vowels, consonants = vowels + 1, 0
        else:
            consonants, vowels = consonants + 1, 0
        longest_consonants = max(longest_consonants, consonants)
        longest_vowels = max(longest_vowels, vowels)
    return longest_consonants, longest_vowels


def is_word(word: str) -> bool:
    if len(word) < MIN_WORD or SAME_THRICE.search(word):
        return False
    if any(word[i : i + 3] in MASH for i in range(len(word) - 2)):
        return False
    consonants, vowels = longest_runs(word)
    return 0 < vowels <= MAX_VOWEL_RUN and consonants <= MAX_CONSONANT_RUN


def is_acronym(token: str) -> bool:
    return token.isupper() and ACRONYM_MIN <= len(token) <= ACRONYM_MAX


def is_meaningful(text: str, *, words: int = 1) -> bool:
    letters = [ch for ch in fold(text) if ch.isalpha()]
    if len(letters) < MIN_LETTERS or len(set(letters)) < MIN_DISTINCT_LETTERS:
        return False
    visible = [ch for ch in text if not ch.isspace()]
    if len(letters) < len(visible) * MIN_WORDLIKE_SHARE:
        return False
    if len(letters) >= VOWEL_CHECK_FROM:
        share = sum(ch in VOWELS for ch in letters) / len(letters)
        if not MIN_VOWEL_SHARE <= share <= MAX_VOWEL_SHARE:
            return False
    tokens = TOKEN.findall(text)
    if any(REPEATED_UNIT.search(fold(token)) for token in tokens):
        return False
    real = {word for token in tokens if is_word(word := fold(token))}
    if len(real) >= max(words, 1):
        return True
    return words <= 1 and any(is_acronym(token) for token in tokens)


def normalize_email(value: str) -> str | None:
    email = value.strip()
    if len(email) > EMAIL_MAX or not EMAIL.match(email):
        return None
    local, domain = email.rsplit("@", 1)
    return f"{local}@{domain.lower()}"
