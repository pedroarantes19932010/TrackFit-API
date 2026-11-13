"""Geração de ficha demonstrativa, bloqueada para perfis de risco."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from trackfit_api.ai_generator import GenerationError, generate_demo
from trackfit_api.identity import identity_db, require_access, require_trainer, current_user
from trackfit_api.storage import save_initial
from trackfit_api.workouts import publish_initial
from trackfit_api.workout_routes import _serialize

router = APIRouter(prefix="/v1/ai", tags=["ai-demo"])


class DemoRequest(BaseModel):
    student_id: str = Field(min_length=1, max_length=120)
    goal: str = Field(pattern="^(general_fitness|strength)$")
    experience: str = Field(pattern="^(beginner|intermediate)$")
    adult: bool
    cleared_for_exercise: bool
    has_pain_or_injury: bool
    has_medical_restriction: bool


@router.post("/demo-workout", status_code=201)
def demo_workout(payload: DemoRequest, user: dict = Depends(require_trainer)):
    if not (payload.adult and payload.cleared_for_exercise
            and not payload.has_pain_or_injury and not payload.has_medical_restriction):
        raise HTTPException(status_code=422, detail="Não elegível para geração automática; avaliação profissional necessária")
    # Antes de chamar API paga, confira vínculo professor-aluno.
    with identity_db() as db:
        require_access(db, user, payload.student_id)
    try:
        exercises = generate_demo(payload.goal, payload.experience)
    except GenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    workout = publish_initial(payload.student_id, exercises, source="ai")
    with identity_db() as db:
        require_access(db, user, payload.student_id)
        save_initial(db, workout)
    return _serialize(workout)

@router.post("/student-demo-workout", status_code=201)
def student_demo_workout(payload: DemoRequest, user: dict = Depends(current_user)):
    """Autogeração demonstrativa: aluno autenticado, com professor vinculado."""
    if user["role"] != "student" or user["user_id"] != payload.student_id:
        raise HTTPException(status_code=403, detail="Somente o próprio aluno")
    if not (payload.adult and payload.cleared_for_exercise
            and not payload.has_pain_or_injury and not payload.has_medical_restriction):
        raise HTTPException(status_code=422, detail="Avaliação profissional necessária")
    # Não gerar fichas sem um professor responsável para revisão posterior.
    with identity_db() as db:
        linked = db.execute(
            "SELECT 1 FROM trainer_students WHERE student_id=? LIMIT 1",
            (user["user_id"],),
        ).fetchone()
        if not linked:
            raise HTTPException(status_code=403, detail="Aluno sem professor vinculado")
    try:
        exercises = generate_demo(payload.goal, payload.experience)
    except GenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    workout = publish_initial(user["user_id"], exercises, source="ai")
    with identity_db() as db:
        # Reválida o vínculo antes da publicação.
        linked = db.execute(
            "SELECT 1 FROM trainer_students WHERE student_id=? LIMIT 1",
            (user["user_id"],),
        ).fetchone()
        if not linked:
            raise HTTPException(status_code=403, detail="Aluno sem professor vinculado")
        save_initial(db, workout)
    return _serialize(workout)
