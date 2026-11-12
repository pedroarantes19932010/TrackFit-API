"""Testa autogeração com IA simulada, sem rede e sem cobrança."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from trackfit_api.identity import identity_db, hash_password
from trackfit_api.main import app
from trackfit_api.workouts import Exercise


class StudentDemoTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        env = patch.dict(os.environ, {"TRACKFIT_DB_PATH": str(Path(temp.name) / "test.sqlite")})
        env.start()
        self.addCleanup(env.stop)
        self.client = TestClient(app)
        with identity_db() as db:
            for uid, role in [("trainer1", "trainer"), ("student1", "student"), ("student2", "student")]:
                db.execute("INSERT INTO users VALUES (?,?,?,?)", (uid, uid, role, hash_password("senha-forte-teste-123")))
            db.execute("INSERT INTO trainer_students VALUES (?,?)", ("trainer1", "student1"))
        self.payload = {"student_id": "student1", "goal": "general_fitness", "experience": "beginner",
                        "adult": True, "cleared_for_exercise": True, "has_pain_or_injury": False,
                        "has_medical_restriction": False}

    def auth(self, username):
        response = self.client.post("/v1/auth/login", json={"username": username, "password": "senha-forte-teste-123"})
        self.assertEqual(response.status_code, 200)
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    def test_student_gets_immediate_version_and_trainer_can_review(self):
        student = self.auth("student1")
        trainer = self.auth("trainer1")
        fake = [Exercise("Remada sentada", 3, 10, 60), Exercise("Mesa flexora", 3, 12, 60),
                Exercise("Supino na máquina", 3, 10, 60)]
        with patch("trackfit_api.ai_routes.generate_demo", return_value=fake) as generator:
            response = self.client.post("/v1/ai/student-demo-workout", json=self.payload, headers=student)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["source"], "ai")
        self.assertEqual(response.json()["version"], 1)
        generator.assert_called_once()
        wid = response.json()["workout_id"]
        self.assertEqual(self.client.get(f"/v1/workouts/{wid}", headers=trainer).status_code, 200)
        revision = self.client.post(f"/v1/workouts/{wid}/revisions", headers=trainer, json={
            "expected_version": 1, "exercises": [{"name": "Remada sentada", "sets": 2, "reps": 12, "rest_seconds": 90}]})
        self.assertEqual(revision.status_code, 201, revision.text)
        self.assertEqual(revision.json()["version"], 2)

    def test_other_student_cannot_generate_for_someone_else(self):
        with patch("trackfit_api.ai_routes.generate_demo") as generator:
            response = self.client.post("/v1/ai/student-demo-workout", json=self.payload, headers=self.auth("student2"))
        self.assertEqual(response.status_code, 403)
        generator.assert_not_called()

    def test_injury_is_blocked_before_api_call(self):
        with patch("trackfit_api.ai_routes.generate_demo") as generator:
            response = self.client.post("/v1/ai/student-demo-workout", json={
                **self.payload, "has_pain_or_injury": True}, headers=self.auth("student1"))
        self.assertEqual(response.status_code, 422)
        generator.assert_not_called()

    def test_unlinked_student_is_blocked(self):
        with patch("trackfit_api.ai_routes.generate_demo") as generator:
            response = self.client.post("/v1/ai/student-demo-workout", json={
                **self.payload, "student_id": "student2"}, headers=self.auth("student2"))
        self.assertEqual(response.status_code, 403)
        generator.assert_not_called()


if __name__ == "__main__":
    unittest.main()
