import pytest

from services.modules import is_meaningful

HONEST_SENTENCES = [
    "Brak opieki dla seniorów na wsi",
    "Mama ma demencję i gubi się na spacerach",
    "Nie mam czym dojechać do lekarza",
    "Samotne matki w Myślenicach",
    "Świetlica dla dzieci po szkole",
    "Wsparcie dla rodzin z Ukrainy",
    "Pomoc PCPR dla rodzin zastępczych",
    "Bezwzględny brak transportu w Szczebrzeszynie",
    "Zmarszczki i chrząszcz w trzcinie",
    "Wstrzymane dowozy obiadów dla chorych",
    "Kawiarenka dla osób starszych, 2 razy w tygodniu",
    "Мені потрібна допомога з житлом",
    "Rower dla trenera z koncertu",
    "Ogród społeczny przy bloku",
]

SINGLE_FIELDS = [
    "Myślenice",
    "Kęty",
    "PCK",
    "MOPS Kraków",
    "Szczebrzeszyn",
    "seniorzy",
    "Fundacja Dobra Wola",
    "osoby z autyzmem",
]

JUNK = [
    "asdfgh asdfgh asdf",
    "asdf qwer zxcv",
    "aaaaaaaaaaaa bbbbbbb",
    "jajajajaja hahahahaha",
    "sdfghjkl qwrtzp",
    "lkajsdlkfj alskdjf alskdj",
    "123456 !!!! ????",
    "qwertyuiop asdfghjkl",
    "zxcvbnm mnbvcxz",
    "dfgdfg ertert",
    "xxxxx yyyyy zzzzz",
    "hjkl hjkl hjkl hjkl",
    "ooooiiiiaaaa eeee",
    "fdsa fdsa jkl",
]


@pytest.mark.parametrize("text", HONEST_SENTENCES)
def test_honest_sentence_passes_with_two_words(text: str) -> None:
    assert is_meaningful(text, words=2)


@pytest.mark.parametrize("text", SINGLE_FIELDS)
def test_short_field_passes(text: str) -> None:
    assert is_meaningful(text)


@pytest.mark.parametrize("text", JUNK)
def test_junk_is_rejected(text: str) -> None:
    assert not is_meaningful(text)
    assert not is_meaningful(text, words=2)


@pytest.mark.parametrize(
    "text",
    [
        "test test test test",
        "aqwsedrftgyhujikolp",
        "Seniorzy",
        "PCPR GOPS MOPS",
        "qwerty qwerty",
    ],
)
def test_two_distinct_real_words_needed(text: str) -> None:
    assert not is_meaningful(text, words=2)


@pytest.mark.parametrize("text", ["asdfgh", "zzzzzz", "qwerty", "sdfg", "xD xD"])
def test_single_junk_field_is_rejected(text: str) -> None:
    assert not is_meaningful(text)
