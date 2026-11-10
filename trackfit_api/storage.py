"""Persistência SQLite local para fichas versionadas; sem endpoint público."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from trackfit_api.workouts import Exercise, Status, WorkoutError, WorkoutVersion


def connect(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path), timeout=10)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("""
        CREATE TABLE IF NOT EXISTS workout_versions (
            workout_id TEXT NOT NULL,
            version INTEGER NOT NULL CHECK (version >= 1),
            student_id TEXT NOT NULL,
            exercises_json TEXT NOT NULL,
            source TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('published', 'superseded')),
            created_at TEXT NOT NULL,
            reviewed_by TEXT,
            PRIMARY KEY (workout_id, version)
        )
    """)
    connection.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS only_one_published_version
        ON workout_versions(workout_id) WHERE status = 'published'
    """)
    connection.commit()
    return connection


def _encode_exercises(exercises: tuple[Exercise, ...]) -> str:
    return json.dumps(
        [{"name": e.name, "sets": e.sets, "reps": e.reps, "rest_seconds": e.rest_seconds}
         for e in exercises], ensure_ascii=False, allow_nan=False
    )


def _decode(row) -> WorkoutVersion:
    return WorkoutVersion(
        workout_id=row[0], version=row[1], student_id=row[2],
        exercises=tuple(Exercise(**item) for item in json.loads(row[3])),
        source=row[4], status=Status(row[5]),
        created_at=datetime.fromisoformat(row[6]), reviewed_by=row[7],
    )


def get_current(connection: sqlite3.Connection, workout_id: str) -> WorkoutVersion | None:
    row = connection.execute(
        """SELECT workout_id, version, student_id, exercises_json, source, status,
                  created_at, reviewed_by FROM workout_versions
           WHERE workout_id = ? AND status = 'published'""", (workout_id,)
    ).fetchone()
    return _decode(row) if row else None


def list_versions(connection: sqlite3.Connection, workout_id: str) -> list[WorkoutVersion]:
    rows = connection.execute(
        """SELECT workout_id, version, student_id, exercises_json, source, status,
                  created_at, reviewed_by FROM workout_versions
           WHERE workout_id = ? ORDER BY version""", (workout_id,)
    ).fetchall()
    return [_decode(row) for row in rows]


def save_initial(connection: sqlite3.Connection, workout: WorkoutVersion) -> None:
    if workout.version != 1 or workout.status != Status.PUBLISHED:
        raise WorkoutError("Ficha inicial inválida.")
    with connection:
        connection.execute(
            "INSERT INTO workout_versions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (workout.workout_id, workout.version, workout.student_id,
             _encode_exercises(workout.exercises), workout.source, workout.status.value,
             workout.created_at.isoformat(), workout.reviewed_by),
        )


def save_revision(
    connection: sqlite3.Connection, old: WorkoutVersion, new: WorkoutVersion
) -> None:
    if (old.workout_id != new.workout_id or old.student_id != new.student_id
            or new.version != old.version + 1
            or old.status != Status.SUPERSEDED or new.status != Status.PUBLISHED
            or not new.reviewed_by):
        raise WorkoutError("Transição de versão inválida.")
    # BEGIN IMMEDIATE serializa escritores e evita sobrescrever revisão concorrente.
    connection.execute("BEGIN IMMEDIATE")
    try:
        current = get_current(connection, old.workout_id)
        if current is None or current.version != old.version:
            raise WorkoutError("Ficha alterada por outra revisão; atualize antes de salvar.")
        connection.execute(
            "UPDATE workout_versions SET status = 'superseded' WHERE workout_id = ? AND version = ?",
            (old.workout_id, old.version),
        )
        connection.execute(
            "INSERT INTO workout_versions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (new.workout_id, new.version, new.student_id,
             _encode_exercises(new.exercises), new.source, new.status.value,
             new.created_at.isoformat(), new.reviewed_by),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
