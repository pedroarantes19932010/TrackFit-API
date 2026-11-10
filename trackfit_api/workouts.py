"""Regras de domínio para fichas versionadas; sem persistência nem IA."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


class WorkoutError(ValueError):
    """Ficha inválida ou transição de estado proibida."""


class Status(str, Enum):
    PUBLISHED = "published"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class Exercise:
    name: str
    sets: int
    reps: int
    rest_seconds: int

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 120:
            raise WorkoutError("Nome do exercício inválido.")
        for field, low, high in (("sets", 1, 20), ("reps", 1, 100), ("rest_seconds", 0, 900)):
            value = getattr(self, field)
            if type(value) is not int or not low <= value <= high:
                raise WorkoutError(f"{field} fora dos limites técnicos.")


@dataclass(frozen=True)
class WorkoutVersion:
    workout_id: str
    version: int
    student_id: str
    exercises: tuple[Exercise, ...]
    source: str
    status: Status
    created_at: datetime
    reviewed_by: str | None = None


def _check_exercises(exercises):
    if not isinstance(exercises, (tuple, list)) or not 1 <= len(exercises) <= 30:
        raise WorkoutError("A ficha precisa de 1 a 30 exercícios.")
    if any(not isinstance(item, Exercise) for item in exercises):
        raise WorkoutError("Exercícios precisam ser objetos Exercise.")
    return tuple(exercises)


def publish_initial(student_id: str, exercises, source: str = "manual") -> WorkoutVersion:
    """Publica uma ficha imediatamente; 'ai' identifica origem, não valida segurança."""
    if not isinstance(student_id, str) or not student_id.strip() or len(student_id) > 120:
        raise WorkoutError("Identificador de aluno inválido.")
    if source not in ("manual", "ai"):
        raise WorkoutError("Origem inválida.")
    return WorkoutVersion(
        workout_id=str(uuid4()), version=1, student_id=student_id.strip(),
        exercises=_check_exercises(exercises), source=source,
        status=Status.PUBLISHED, created_at=datetime.now(timezone.utc)
    )


def revise(current: WorkoutVersion, exercises, reviewer_id: str) -> tuple[WorkoutVersion, WorkoutVersion]:
    """Retorna versão anterior arquivada e nova versão publicada; não altera objetos existentes."""
    if not isinstance(current, WorkoutVersion) or current.status != Status.PUBLISHED:
        raise WorkoutError("Somente a versão publicada pode ser revisada.")
    if not isinstance(reviewer_id, str) or not reviewer_id.strip() or len(reviewer_id) > 120:
        raise WorkoutError("Revisor inválido.")
    checked = _check_exercises(exercises)
    archived = replace(current, status=Status.SUPERSEDED)
    updated = replace(
        current, version=current.version + 1, exercises=checked,
        source="manual", status=Status.PUBLISHED,
        reviewed_by=reviewer_id.strip(), created_at=datetime.now(timezone.utc)
    )
    return archived, updated
