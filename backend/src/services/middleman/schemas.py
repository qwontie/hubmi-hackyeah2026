import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from services.modules import InnovationRef

PLACE_MAX = 120
CONTEXT_MIN = 20
CONTEXT_MAX = 3000
POWIAT_PATTERN = r"^[a-z0-9-]{2,60}$"


class InstitutionType(StrEnum):
    GMINA = "gmina"
    POWIAT = "powiat"
    OPS = "ops"
    CUS = "cus"
    PCPR = "pcpr"
    NGO = "ngo"
    SCHOOL = "school"
    SENIOR = "senior"
    HEALTH = "health"
    OTHER = "other"


INSTITUTION_NAMES: dict[InstitutionType, str] = {
    InstitutionType.GMINA: "Urząd gminy",
    InstitutionType.POWIAT: "Starostwo powiatowe",
    InstitutionType.OPS: "Ośrodek pomocy społecznej",
    InstitutionType.CUS: "Centrum usług społecznych",
    InstitutionType.PCPR: "Powiatowe centrum pomocy rodzinie",
    InstitutionType.NGO: "Organizacja pozarządowa",
    InstitutionType.SCHOOL: "Szkoła lub placówka oświatowa",
    InstitutionType.SENIOR: "Dzienny dom lub klub seniora",
    InstitutionType.HEALTH: "Placówka ochrony zdrowia",
    InstitutionType.OTHER: "Inna instytucja",
}


class InstitutionOption(BaseModel):
    slug: InstitutionType
    name: str


class AdaptIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_type: InstitutionType
    place: str = Field(max_length=PLACE_MAX)
    powiat: str | None = Field(default=None, pattern=POWIAT_PATTERN)
    context: str = Field(max_length=CONTEXT_MAX)


class Step(BaseModel):
    title: str = Field(description="Krótka nazwa kroku, do 8 słów.")
    description: str = Field(description="Co konkretnie zrobić, 1 do 3 zdań.")


class Risk(BaseModel):
    risk: str = Field(description="Ryzyko dla tej instytucji, jedno zdanie.")
    mitigation: str = Field(description="Jak je ograniczyć, jedno zdanie.")


class Combination(BaseModel):
    slug: str = Field(description="Slug innowacji z listy kandydatów, bez zmian.")
    why: str = Field(description="Dlaczego warto ją połączyć, jedno zdanie.")


class ServicePlan(BaseModel):
    unclear: bool = Field(
        description=(
            "true tylko wtedy, gdy opis instytucji to przypadkowe znaki "
            "lub tekst bez związku z usługami społecznymi"
        )
    )
    service_name: str = Field(description="Nazwa usługi dla tej instytucji.")
    summary: str = Field(
        description="Czym będzie ta usługa w tej instytucji, 2 do 4 zdań."
    )
    target_group: str = Field(
        description="Do kogo trafi usługa w tym miejscu, 1 do 3 zdań."
    )
    steps: list[Step] = Field(description="Kroki uruchomienia, od 4 do 7.")
    staff: list[str] = Field(description="Kogo z personelu potrzeba, 2 do 5.")
    partners: list[str] = Field(description="Z kim współpracować lokalnie, 2 do 5.")
    cost_drivers: list[str] = Field(
        description="Od czego zależy koszt, rodzaje kosztów bez kwot, 3 do 6."
    )
    risks: list[Risk] = Field(description="Ryzyka, 2 do 4.")
    measures: list[str] = Field(description="Co mierzyć, aby wiedzieć, że działa.")
    combine: list[Combination] = Field(
        description="0 do 3 innowacji z listy kandydatów, które dobrze uzupełniają."
    )
    to_check: list[str] = Field(
        description=(
            "Czego nie ma w źródłach, a instytucja musi sprawdzić sama, 1 do 4."
        )
    )
    local_context: str = Field(
        default="",
        description=(
            "1 do 3 zdań: co z sekcji DANE ROPS ma znaczenie dla tej usługi w tym "
            "miejscu; każdą liczbę podaj z rokiem; pusty tekst, gdy tej sekcji nie ma."
        ),
    )


class LocalFact(BaseModel):
    label: str
    value: float
    unit: str
    year: int
    region_value: float | None
    source_title: str
    source_url: str
    page: int | None

    def sentence(self) -> str:
        unit = self.unit if self.unit in {"", "%"} else f" {self.unit}"
        text = f"{self.label}: {self.value:g}{unit} ({self.year})"
        if self.region_value is not None:
            text += f", w całej Małopolsce {self.region_value:g}{unit}"
        page = f", s. {self.page}" if self.page else ""
        return f"{text}. Źródło: {self.source_title}{page}."


class LocalChallenge(BaseModel):
    slug: str
    title: str
    area: str
    summary: str
    source_title: str
    source_url: str
    pages: list[int]


class CombinedInnovation(BaseModel):
    slug: str
    title: str
    lead: str
    why: str


class Plan(BaseModel):
    service_name: str
    summary: str
    target_group: str
    steps: list[Step]
    staff: list[str]
    partners: list[str]
    cost_drivers: list[str]
    risks: list[Risk]
    measures: list[str]
    combine: list[CombinedInnovation]
    to_check: list[str]
    local_context: str = ""
    local_facts: list[LocalFact] = []
    regional_challenges: list[LocalChallenge] = []


class AdaptationOut(BaseModel):
    id: uuid.UUID
    share_path: str
    innovation: InnovationRef
    institution: InstitutionOption
    place: str
    powiat: str | None
    context: str
    plan: Plan
    created_at: datetime


class AdminAdaptation(BaseModel):
    id: uuid.UUID
    share_path: str
    innovation: InnovationRef
    institution: InstitutionOption
    place: str
    powiat: str | None
    context: str
    service_name: str
    created_at: datetime
