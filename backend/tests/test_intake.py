import pytest

from services.needs.intake import (
    MAX_TEXT,
    SPAM,
    TOO_FEW_WORDS,
    TOO_LONG,
    TOO_MANY_LINKS,
    TOO_SHORT,
    TextRejectedError,
    dedupe_key,
    first_words,
    intake_text,
)

GOOD = "Mama ma demencję i nie radzę sobie z opieką po pracy."


def code_of(text: str, honeypot: str | None = None) -> tuple[str, str]:
    with pytest.raises(TextRejectedError) as caught:
        intake_text(text, honeypot=honeypot)
    return caught.value.code, caught.value.field


def test_good_text_is_kept_as_written_with_whitespace_collapsed() -> None:
    assert intake_text(f"  {GOOD}\n\n ") == GOOD


def test_honeypot_rejects_on_the_website_field() -> None:
    assert code_of(GOOD, honeypot="https://spam.example") == (SPAM, "website")


def test_blank_honeypot_is_ignored() -> None:
    assert intake_text(GOOD, honeypot="  ") == GOOD


def test_too_short() -> None:
    assert code_of("za mało") == (TOO_SHORT, "text")


def test_too_long() -> None:
    assert code_of("słowo " * (MAX_TEXT // 5)) == (TOO_LONG, "text")


def test_one_word_is_not_enough() -> None:
    assert code_of("Samotnośććććććć") == (TOO_FEW_WORDS, "text")


def test_numbers_and_symbols_are_not_words() -> None:
    assert code_of("123456 !!! 789 ???") == (TOO_FEW_WORDS, "text")


def test_two_links_pass_three_do_not() -> None:
    two = f"{GOOD} https://a.pl www.b.pl"
    assert intake_text(two) == two
    assert code_of(f"{two} http://c.pl") == (TOO_MANY_LINKS, "text")


def test_unclear_text_is_not_rejected_by_intake() -> None:
    text = "asdf qwer zxcv uiop"
    assert intake_text(text) == text


def test_first_words_makes_a_short_title() -> None:
    assert first_words(GOOD) == "Mama ma demencję i nie radzę sobie z…"
    assert first_words("Brak opieki nad seniorem") == "Brak opieki nad seniorem"


def test_dedupe_key_ignores_case_and_spacing_but_not_client() -> None:
    key = dedupe_key("1.2.3.4", GOOD)
    assert dedupe_key("1.2.3.4", f"  {GOOD.upper()} ") == key
    assert dedupe_key("5.6.7.8", GOOD) != key
