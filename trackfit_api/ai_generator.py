"""Protótipo de geração com OpenAI; somente perfis de teste sem restrições."""
import json
import os
import urllib.error
import urllib.request

from trackfit_api.workouts import Exercise, WorkoutError
from trackfit_api.catalog_routes import CATALOG as EXERCISE_CATALOG

# Catálogo deliberadamente restrito para testes; não constitui prescrição clínica.
# IDs legados mantidos para compatibilidade com o prompt e os testes.
# Os nomes vêm da biblioteca única exposta ao aplicativo.
AI_TO_CATALOG_ID = {
    "agachamento_livre": "squat_bodyweight",
    "remada_sentada": "seated_row",
    "supino_maquina": "machine_chest_press",
    "puxada_frontal": "lat_pulldown",
    "cadeira_extensora": "leg_extension",
    "mesa_flexora": "leg_curl",
}
_catalog_by_id = {exercise.exercise_id: exercise for exercise in EXERCISE_CATALOG}
if not set(AI_TO_CATALOG_ID.values()).issubset(_catalog_by_id):
    raise RuntimeError("Catálogo público e gerador de IA inconsistentes")
CATALOG = {
    ai_id: _catalog_by_id[catalog_id].name
    for ai_id, catalog_id in AI_TO_CATALOG_ID.items()
}
MAX_BYTES = 12000


class GenerationError(RuntimeError):
    pass


def generate_demo(goal: str, experience: str) -> list[Exercise]:
    """Uma chamada limitada, sem nome, histórico médico ou dados pessoais."""
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise GenerationError("OPENAI_API_KEY não configurada")
    model = os.environ.get("TRACKFIT_WORKOUT_MODEL", "gpt-4.1-mini")
    if model != "gpt-4.1-mini":
        raise GenerationError("Modelo não permitido no protótipo")
    prompt = (
        "Você é um gerador de fichas demonstrativas para TESTES, não um profissional "
        "responsável por prescrições. Gere 3 a 5 exercícios simples. "
        "Use exclusivamente IDs do catálogo: " + ", ".join(CATALOG) + ". "
        "Responda SOMENTE JSON com formato "
        '{"exercises":[{"id":"remada_sentada","sets":3,"reps":10,"rest_seconds":60}]}. '
        "Não inclua texto extra. Limites: sets 1-4, reps 6-15, descanso 45-180 segundos. "
        f"Objetivo: {goal}. Experiência: {experience}."
    )
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps({"model": model, "input": prompt, "max_output_tokens": 500, "store": False}).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read(MAX_BYTES + 1)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        raise GenerationError("Serviço de geração indisponível") from exc
    if len(raw) > MAX_BYTES:
        raise GenerationError("Resposta excedeu limite")
    try:
        result = json.loads(raw)
        if result.get("status") != "completed":
            raise ValueError("Resposta incompleta")
        text = "".join(
            part["text"]
            for item in result.get("output", []) if item.get("type") == "message"
            for part in item.get("content", []) if part.get("type") == "output_text"
        )
        entries = json.loads(text)["exercises"]
        if not isinstance(entries, list) or not 3 <= len(entries) <= 5:
            raise ValueError("Quantidade inválida")
        exercises = []
        seen = set()
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"id", "sets", "reps", "rest_seconds"}:
                raise ValueError("Campos inválidos")
            exercise_id = entry["id"]
            if exercise_id not in CATALOG or exercise_id in seen:
                raise ValueError("Exercício inválido ou repetido")
            seen.add(exercise_id)
            if not (type(entry["sets"]) is int and 1 <= entry["sets"] <= 4
                    and type(entry["reps"]) is int and 6 <= entry["reps"] <= 15
                    and type(entry["rest_seconds"]) is int and 45 <= entry["rest_seconds"] <= 180):
                raise ValueError("Parâmetros inválidos")
            exercises.append(Exercise(CATALOG[exercise_id], entry["sets"], entry["reps"], entry["rest_seconds"]))
        return exercises
    except (KeyError, TypeError, ValueError, WorkoutError, json.JSONDecodeError) as exc:
        raise GenerationError("Resposta da IA reprovada na validação") from exc
