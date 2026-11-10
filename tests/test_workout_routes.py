import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from trackfit_api.main import app


class WorkoutRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {
            "TRACKFIT_DB_PATH": str(Path(self.temp.name) / "db.sqlite"),
            "TRACKFIT_DEV_API_KEY": "a" * 40,
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = TestClient(app)
        self.headers = {"x-trackfit-key": "a" * 40}
        self.payload = {
            "student_id": "aluno-ficticio",
            "exercises": [{"name": "Remada", "sets": 3, "reps": 12, "rest_seconds": 60}],
        }

    def test_sem_chave_retorna_401(self):
        self.assertEqual(self.client.post("/v1/workouts", json=self.payload).status_code, 401)
        self.assertEqual(self.client.get("/v1/workouts/id-inexistente").status_code, 401)

    def test_fluxo_publicacao_revisao_historico(self):
        result = self.client.post("/v1/workouts", json=self.payload, headers=self.headers)
        self.assertEqual(result.status_code, 201, result.text)
        workout = result.json()
        self.assertEqual(workout["version"], 1)
        workout_id = workout["workout_id"]
        response = self.client.get(f"/v1/workouts/{workout_id}", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        revised = self.client.post(
            f"/v1/workouts/{workout_id}/revisions",
            headers=self.headers,
            json={"expected_version": 1, "reviewer_id": "prof-ficticio",
                  "exercises": [{"name": "Supino", "sets": 3, "reps": 10, "rest_seconds": 90}]},
        )
        self.assertEqual(revised.status_code, 201, revised.text)
        self.assertEqual(revised.json()["version"], 2)
        history = self.client.get(f"/v1/workouts/{workout_id}/versions", headers=self.headers)
        self.assertEqual([x["version"] for x in history.json()], [1, 2])
        self.assertEqual(history.json()[0]["status"], "superseded")
        self.assertEqual(self.client.post(
            f"/v1/workouts/{workout_id}/revisions", headers=self.headers,
            json={"expected_version": 1, "reviewer_id": "prof-ficticio",
                  "exercises": self.payload["exercises"]},
        ).status_code, 409)

    def test_invalid_input(self):
        bad = dict(self.payload, exercises=[])
        self.assertEqual(self.client.post("/v1/workouts", json=bad, headers=self.headers).status_code, 422)

    def test_no_key_configured(self):
        with patch.dict(os.environ, {"TRACKFIT_DEV_API_KEY": ""}):
            self.assertEqual(self.client.post("/v1/workouts", json=self.payload, headers=self.headers).status_code, 401)


if __name__ == "__main__":
    unittest.main()
