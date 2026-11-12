"""Catálogo editorial de exercícios; links externos opcionais, sem download de vídeos."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/exercises", tags=["exercise-catalog"])


class ExerciseVideo(BaseModel):
    youtube_id: str = Field(pattern=r"^[A-Za-z0-9_-]{11}$")
    kind: str = Field(pattern="^(demonstration|common_mistakes|tips)$")
    creator_name: str = Field(min_length=1, max_length=100)


class CatalogExercise(BaseModel):
    exercise_id: str
    name: str
    muscle_group: str
    equipment: str
    instructions: list[str]
    videos: list[ExerciseVideo] = Field(default_factory=list)


# IDs estáveis permitem associar fichas e vídeos sem depender do nome exibido.
# Nenhum vídeo de terceiros é incluído sem curadoria editorial.
CATALOG = (
    CatalogExercise(exercise_id="squat_bodyweight", name="Agachamento livre",
                    muscle_group="pernas", equipment="peso corporal",
                    instructions=["Mantenha os pés apoiados.", "Flexione quadril e joelhos de forma controlada."]),
    CatalogExercise(exercise_id="seated_row", name="Remada sentada",
                    muscle_group="costas", equipment="máquina",
                    instructions=["Ajuste o banco.", "Puxe a alça de forma controlada."]),
    CatalogExercise(exercise_id="machine_chest_press", name="Supino na máquina",
                    muscle_group="peitoral", equipment="máquina",
                    instructions=["Ajuste o assento.", "Empurre sem perder o controle do movimento."]),
    CatalogExercise(exercise_id="leg_curl", name="Mesa flexora",
                    muscle_group="posteriores", equipment="máquina",
                    instructions=["Ajuste o equipamento.", "Flexione os joelhos de forma controlada."]),
    CatalogExercise(exercise_id="calf_raise", name="Elevação de panturrilha",
                    muscle_group="panturrilhas", equipment="peso corporal",
                    instructions=["Mantenha apoio estável.", "Eleve e abaixe os calcanhares lentamente."]),
    CatalogExercise(exercise_id="lat_pulldown", name="Puxada frontal",
                    muscle_group="costas", equipment="máquina",
                    instructions=["Ajuste o assento e apoio.", "Puxe de forma controlada sem compensar com o tronco."]),
    CatalogExercise(exercise_id="leg_extension", name="Cadeira extensora",
                    muscle_group="pernas", equipment="máquina",
                    instructions=["Ajuste o banco e apoio.", "Estenda os joelhos de forma controlada."]),
    CatalogExercise(exercise_id="plank", name="Prancha",
                    muscle_group="core", equipment="colchonete",
                    instructions=["Apoie antebraços e pés.", "Mantenha alinhamento confortável."]),
)


@router.get("", response_model=list[CatalogExercise])
def list_exercises(muscle_group: str | None = Query(default=None, max_length=50),
                   search: str | None = Query(default=None, max_length=80)):
    results = CATALOG
    if muscle_group:
        results = tuple(e for e in results if e.muscle_group.casefold() == muscle_group.casefold())
    if search:
        results = tuple(e for e in results if search.casefold() in e.name.casefold())
    return list(results)


@router.get("/{exercise_id}", response_model=CatalogExercise)
def get_exercise(exercise_id: str):
    for exercise in CATALOG:
        if exercise.exercise_id == exercise_id:
            return exercise
    raise HTTPException(status_code=404, detail="Exercício não encontrado")
