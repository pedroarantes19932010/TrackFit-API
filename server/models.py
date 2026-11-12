"""Contratos do piloto. Os limites técnicos não substituem avaliação profissional."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class Profile(Strict):
    age: int = Field(ge=18, le=100)
    goal: Literal["condicionamento", "hipertrofia"]
    experience: Literal["iniciante", "intermediario"]
    days: int = Field(ge=1, le=6)
    minutes: int = Field(ge=15, le=120)
    equipment: Literal["academia", "casa"]
    needs_review: bool  # dor, lesão, condição de saúde, gestação ou dúvida
    limitations: str = Field(max_length=1000)
    consent: Literal[True]

class Exercise(Strict):
    exercise_id: str | None = None

    @field_validator("exercise_id")
    @classmethod
    def known_catalog_id(cls,value):
        from trackfit_api.catalog_routes import CATALOG
        if value is not None and not any(e.exercise_id == value for e in CATALOG):
            raise ValueError("Referência de catálogo desconhecida.")
        return value

    name: str = Field(min_length=2, max_length=100)
    sets: int = Field(ge=1, le=6)
    reps: int = Field(ge=1, le=30)
    rest_seconds: int = Field(ge=15, le=300)
    instructions: str = Field(min_length=1, max_length=500)

class Day(Strict):
    title: str = Field(min_length=1, max_length=80)
    exercises: list[Exercise] = Field(min_length=1, max_length=12)

class Template(Strict):
    name: str = Field(min_length=2, max_length=100)
    goal: Literal["condicionamento", "hipertrofia"]
    experience: Literal["iniciante", "intermediario"]
    equipment: Literal["academia", "casa"]
    minutes: int = Field(ge=15, le=120)
    min_age: int = Field(ge=18, le=100)
    max_age: int = Field(ge=18, le=100)
    days: list[Day] = Field(min_length=1, max_length=6)

class TemplateApproval(Strict):
    approved: bool

class NewStudent(Strict):
    name: str = Field(min_length=2, max_length=80)

class Generate(Strict):
    request_id: str = Field(pattern=r"^[a-zA-Z0-9-]{16,64}$")
    profile: Profile

class Review(Strict):
    expected_version: int = Field(ge=1)
    action: Literal["approve", "edit", "suspend"]
    note: str = Field(min_length=3, max_length=1000)
    days: list[Day] | None = Field(default=None, min_length=1, max_length=6)

class Start(Strict):
    request_id: str = Field(pattern=r"^[a-zA-Z0-9-]{16,64}$")
    expected_version: int = Field(ge=1)
    day: int = Field(ge=0, le=5)

class PerformedSet(Strict):
    exercise_index: int = Field(ge=0, le=11)
    set_index: int = Field(ge=0, le=5)
    weight_kg: float = Field(ge=0, le=1000, allow_inf_nan=False)
    reps: int = Field(ge=0, le=100)

class Finish(Strict):
    sets: list[PerformedSet] = Field(min_length=1, max_length=72)
    note: str = Field(max_length=1000)
