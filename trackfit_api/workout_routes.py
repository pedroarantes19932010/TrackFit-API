"""Endpoints de fichas para protótipo local; não adequados a produção."""
import hmac
import os
import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from trackfit_api.storage import connect, get_current, list_versions, save_initial, save_revision
from trackfit_api.workouts import Exercise, WorkoutError, publish_initial, revise

router = APIRouter(prefix="/v1/workouts", tags=["workouts"])


def require_prototype_key(x_trackfit_key: str | None = Header(default=None)) -> None:
    """Chave compartilhada somente para desenvolvimento; não identifica usuários."""
    expected = os.environ.get("TRACKFIT_DEV_API_KEY", "")
    if len(expected) < 32 or not x_trackfit_key or not hmac.compare_digest(expected, x_trackfit_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Acesso não autorizado")


def database_path() -> Path:
    path = os.environ.get("TRACKFIT_DB_PATH")
    if not path:
        raise HTTPException(status_code=503, detail="Banco de desenvolvimento não configurado")
    return Path(path)


class ExerciseInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    sets: int = Field(ge=1, le=20)
    reps: int = Field(ge=1, le=100)
    rest_seconds: int = Field(ge=0, le=900)


class CreateWorkout(BaseModel):
    student_id: str = Field(min_length=1, max_length=120)
    exercises: list[ExerciseInput] = Field(min_length=1, max_length=30)


class ReviseWorkout(BaseModel):
    expected_version: int = Field(ge=1)
    reviewer_id: str = Field(min_length=1, max_length=120)
    exercises: list[ExerciseInput] = Field(min_length=1, max_length=30)


def _exercises(values: list[ExerciseInput]) -> list[Exercise]:
    return [Exercise(**item.model_dump()) for item in values]


def _serialize(workout):
    return {
        "workout_id": workout.workout_id, "version": workout.version,
        "student_id": workout.student_id,
        "exercises": [{"name": e.name, "sets": e.sets, "reps": e.reps,
                       "rest_seconds": e.rest_seconds} for e in workout.exercises],
        "source": workout.source, "status": workout.status.value,
        "created_at": workout.created_at.isoformat(), "reviewed_by": workout.reviewed_by,
    }


@router.post("", status_code=201, dependencies=[Depends(require_prototype_key)])
def create_workout(payload: CreateWorkout):
    try:
        workout = publish_initial(payload.student_id, _exercises(payload.exercises), source="manual")
        with connect(database_path()) as db:
            save_initial(db, workout)
        return _serialize(workout)
    except WorkoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{workout_id}", dependencies=[Depends(require_prototype_key)])
def read_workout(workout_id: str):
    with connect(database_path()) as db:
        current = get_current(db, workout_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Ficha não encontrada")
    return _serialize(current)


@router.get("/{workout_id}/versions", dependencies=[Depends(require_prototype_key)])
def read_versions(workout_id: str):
    with connect(database_path()) as db:
        versions = list_versions(db, workout_id)
    if not versions:
        raise HTTPException(status_code=404, detail="Ficha não encontrada")
    return [_serialize(item) for item in versions]


@router.post("/{workout_id}/revisions", status_code=201, dependencies=[Depends(require_prototype_key)])
def revise_workout(workout_id: str, payload: ReviseWorkout):
    try:
        with connect(database_path()) as db:
            current = get_current(db, workout_id)
            if current is None:
                raise HTTPException(status_code=404, detail="Ficha não encontrada")
            if current.version != payload.expected_version:
                raise HTTPException(status_code=409, detail="Versão desatualizada")
            old, new = revise(current, _exercises(payload.exercises), payload.reviewer_id)
            save_revision(db, old, new)
        return _serialize(new)
    except WorkoutError as exc:
        if "alterada por outra revisão" in str(exc):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Conflito de versão") from exc
