"""Endpoints de fichas para protótipo local; não adequados a produção."""
import os
import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from trackfit_api.storage import get_current, list_versions, save_initial, save_revision
from trackfit_api.identity import identity_db, current_user, require_trainer, require_access
from trackfit_api.workouts import Exercise, WorkoutError, publish_initial, revise

router = APIRouter(prefix="/v1/workouts", tags=["workouts"])


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


@router.post("", status_code=201)
def create_workout(payload: CreateWorkout, user: dict = Depends(require_trainer)):
    try:
        workout = publish_initial(payload.student_id, _exercises(payload.exercises), source="manual")
        with identity_db() as db:
            require_access(db, user, payload.student_id)
            save_initial(db, workout)
        return _serialize(workout)
    except WorkoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/pending-review")
def pending_review(user: dict = Depends(require_trainer)):
    """Fichas de IA dos alunos vinculados ainda não revisadas pelo professor."""
    with identity_db() as db:
        rows = db.execute(
            """SELECT w.workout_id FROM workout_versions w
               JOIN trainer_students ts ON ts.student_id=w.student_id
               WHERE ts.trainer_id=? AND w.status='published' AND w.source='ai'
                 AND NOT EXISTS (
                   SELECT 1 FROM workout_versions r
                   WHERE r.workout_id=w.workout_id AND r.reviewed_by IS NOT NULL
                 )
               ORDER BY w.created_at ASC LIMIT 100""",
            (user["user_id"],),
        ).fetchall()
        return [_serialize(get_current(db, row[0])) for row in rows]


@router.get("/{workout_id}")
def read_workout(workout_id: str, user: dict = Depends(current_user)):
    with identity_db() as db:
        current = get_current(db, workout_id)
        if current is not None:
            require_access(db, user, current.student_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Ficha não encontrada")
    return _serialize(current)


@router.get("/{workout_id}/versions")
def read_versions(workout_id: str, user: dict = Depends(current_user)):
    with identity_db() as db:
        versions = list_versions(db, workout_id)
        if versions:
            require_access(db, user, versions[0].student_id)
    if not versions:
        raise HTTPException(status_code=404, detail="Ficha não encontrada")
    return [_serialize(item) for item in versions]


@router.post("/{workout_id}/revisions", status_code=201)
def revise_workout(workout_id: str, payload: ReviseWorkout, user: dict = Depends(require_trainer)):
    try:
        with identity_db() as db:
            current = get_current(db, workout_id)
            if current is None:
                raise HTTPException(status_code=404, detail="Ficha não encontrada")
            require_access(db, user, current.student_id)
            if current.version != payload.expected_version:
                raise HTTPException(status_code=409, detail="Versão desatualizada")
            old, new = revise(current, _exercises(payload.exercises), user['user_id'])
            save_revision(db, old, new)
        return _serialize(new)
    except WorkoutError as exc:
        if "alterada por outra revisão" in str(exc):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Conflito de versão") from exc
