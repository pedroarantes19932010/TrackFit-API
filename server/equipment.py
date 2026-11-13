"""Resolve apenas a alternativa prescrita no próprio modelo aprovado."""
from trackfit_api.catalog_routes import CATALOG

REQUIRED = {e.exercise_id:e.equipment for e in CATALOG}


def adapt_equipment(template, inventory):
    available = set(inventory or []) | {"peso corporal"}
    days = []
    for day in template["days"]:
        exercises = []
        used = set()
        replacements = set()
        for entry in day["exercises"]:
            primary = {k:v for k,v in entry.items() if k != "alternative"}
            exercise_id = primary.get("exercise_id")
            if inventory is not None and REQUIRED.get(exercise_id) not in available:
                alternate = entry.get("alternative")
                if not alternate or REQUIRED.get(alternate.get("exercise_id")) not in available:
                    return None
                primary = dict(alternate)
                exercise_id = primary["exercise_id"]
                if exercise_id in used:
                    return None
                replacements.add(exercise_id)
            elif exercise_id in replacements:
                return None
            used.add(exercise_id)
            exercises.append(primary)
        days.append({**day,"exercises":exercises})
    return {**template,"days":days}
