import re
from collections.abc import Iterable

NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
LEGAL = re.compile(
    r"\b(ustaw\w*|rozporządze\w*|art\.|dz\.\s?u\.?|kodeks\w*|paragraf\w*|"
    r"pfron|nfz|efs\+?|fers|fem|rpo\w*|kpo|fundusz\w*|grant\w*|"
    r"konkurs\w*|nabór|naboru|dofinansowani\w*)",
    re.IGNORECASE,
)


def _numbers(text: str) -> set[str]:
    return {match.replace(",", ".") for match in NUMBER.findall(text)}


def _legal(text: str) -> set[str]:
    return {match.lower()[:5] for match in LEGAL.findall(text)}


class Sources:
    def __init__(self, texts: Iterable[str]) -> None:
        joined = "\n".join(texts)
        self.numbers = _numbers(joined)
        self.legal = _legal(joined)

    def invented(self, text: str) -> list[str]:
        numbers = sorted(_numbers(text) - self.numbers)
        legal = sorted(_legal(text) - self.legal)
        return numbers + legal

    def clean_list(self, items: Iterable[str]) -> list[str]:
        return [item for item in items if not self.invented(item)]

    def clean_text(self, text: str) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        kept = [sentence for sentence in sentences if not self.invented(sentence)]
        return " ".join(kept)
