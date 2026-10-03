import re

ORGANIZATION_MARKERS = (
    "fundacj",
    "fudacj",
    "stowarzyszeni",
    "gmina",
    "gminy",
    "powiat",
    "miasto",
    "miasta",
    "ośrod",
    "osrod",
    "ops ",
    "mops",
    "gops",
    "pcpr",
    "sp. z o",
    "sp.z o",
    "spółk",
    "spółdziel",
    "s.a.",
    "politechnik",
    "uniwersytet",
    "akademi",
    "instytut",
    "szpital",
    "spzoz",
    "centrum",
    "przedsiębiorstw",
    "szkoł",
    "przedszkol",
    "zespół",
    "urząd",
    "towarzystw",
    "związek",
    "caritas",
    "parafi",
    "teatr",
    "muzeum",
    "bibliotek",
    "klub",
    "kooperatyw",
    "uczelni",
    "wydział",
    "dom pomocy",
    "regionalny",
    "regionalna",
)

FIRST_NAMES = frozenset(
    [
        "ewa",
        "anna",
        "maria",
        "katarzyna",
        "małgorzata",
        "agnieszka",
        "barbara",
        "krystyna",
        "elżbieta",
        "joanna",
        "magdalena",
        "monika",
        "teresa",
        "zofia",
        "danuta",
        "beata",
        "jadwiga",
        "aleksandra",
        "natalia",
        "dorota",
        "halina",
        "irena",
        "karolina",
        "marta",
        "justyna",
        "urszula",
        "sylwia",
        "agata",
        "iwona",
        "grażyna",
        "alicja",
        "paulina",
        "renata",
        "wiesława",
        "gabriela",
        "klaudia",
        "patrycja",
        "bożena",
        "czesława",
        "kamila",
        "jan",
        "piotr",
        "krzysztof",
        "andrzej",
        "tomasz",
        "paweł",
        "michał",
        "marcin",
        "stanisław",
        "jakub",
        "adam",
        "marek",
        "łukasz",
        "grzegorz",
        "mateusz",
        "wojciech",
        "mariusz",
        "dariusz",
        "zbigniew",
        "jerzy",
        "maciej",
        "rafał",
        "kamil",
        "robert",
        "józef",
        "jacek",
        "bartosz",
        "dawid",
        "mirosław",
        "konrad",
        "miłosz",
        "tadeusz",
        "ryszard",
        "henryk",
        "kazimierz",
        "sławomir",
        "artur",
        "damian",
        "przemysław",
        "sebastian",
        "daniel",
        "bartłomiej",
        "ivan",
        "volodymyr",
    ]
)
PATRON_MARKERS = frozenset({"im.", "im", "imienia"})
DASH_SPLIT = re.compile(r"\s+[-–]\s+")


def is_organization(line: str) -> bool:
    lowered = f"{line.lower()} "
    return any(marker in lowered for marker in ORGANIZATION_MARKERS)


def names_a_person(line: str) -> bool:
    tokens = line.replace(",", " ").split()
    for index, token in enumerate(tokens):
        if token.lower().strip("\"„”'") not in FIRST_NAMES:
            continue
        previous = tokens[index - 1].lower() if index else ""
        if previous not in PATRON_MARKERS:
            return True
    return False


def clean_line(line: str) -> str:
    line = line.replace("\u200b", "").replace("\xa0", " ").strip()
    line = re.sub(r"^[-–•]\s*", "", line)
    return re.sub(r"\s+", " ", line).strip(" ,;:")


def organizations(lines: list[str]) -> list[str]:
    result: list[str] = []
    for raw in lines:
        line = clean_line(raw)
        if not line or not is_organization(line):
            continue
        parts = [p for p in DASH_SPLIT.split(line) if p]
        kept = " - ".join(p for p in parts if is_organization(p)) or line
        if names_a_person(kept):
            continue
        if kept not in result:
            result.append(kept)
    return result
