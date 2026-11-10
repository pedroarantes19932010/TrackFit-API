import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from trackfit_api.identity import hash_password, identity_db, verify_password
from trackfit_api.main import app


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {"TRACKFIT_DB_PATH": str(Path(self.temp.name) / "auth.sqlite")})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = TestClient(app)
        with identity_db() as db:
            db.execute("INSERT INTO users VALUES (?,?,?,?)", ("trainer1", "prof", "trainer", hash_password("senha-muito-forte-123")))
            db.execute("INSERT INTO users VALUES (?,?,?,?)", ("student1", "aluno", "student", hash_password("senha-muito-forte-456")))
            db.execute("INSERT INTO users VALUES (?,?,?,?)", ("student2", "outro", "student", hash_password("senha-muito-forte-789")))
            db.execute("INSERT INTO trainer_students VALUES (?,?)", ("trainer1", "student1"))

    def login(self, username, password):
        response = self.client.post("/v1/auth/login", json={"username": username, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    def test_password(self):
        digest = hash_password("senha-muito-forte-123")
        self.assertTrue(verify_password("senha-muito-forte-123", digest))
        self.assertFalse(verify_password("outra-senha-123", digest))

    def test_login_me(self):
        self.assertEqual(self.client.get("/v1/auth/me").status_code, 401)
        self.assertEqual(self.client.post("/v1/auth/login", json={"username": "prof", "password": "errada"}).status_code, 401)
        headers = self.login("prof", "senha-muito-forte-123")
        self.assertEqual(self.client.get("/v1/auth/me", headers=headers).json()["role"], "trainer")

    def test_access_controls(self):
        trainer = self.login("prof", "senha-muito-forte-123")
        student = self.login("aluno", "senha-muito-forte-456")
        outsider = self.login("outro", "senha-muito-forte-789")
        payload = {"student_id": "student1", "exercises": [{"name": "Remada", "sets": 3, "reps": 12, "rest_seconds": 60}]}
        self.assertEqual(self.client.post("/v1/workouts", json=payload, headers=student).status_code, 403)
        result = self.client.post("/v1/workouts", json=payload, headers=trainer)
        self.assertEqual(result.status_code, 201, result.text)
        workout_id = result.json()["workout_id"]
        self.assertEqual(self.client.get(f"/v1/workouts/{workout_id}", headers=student).status_code, 200)
        self.assertEqual(self.client.get(f"/v1/workouts/{workout_id}", headers=outsider).status_code, 403)
        self.assertEqual(self.client.post(f"/v1/workouts/{workout_id}/revisions", headers=student, json={
            "expected_version": 1, "exercises": payload["exercises"]}).status_code, 403)


if __name__ == "__main__":
    unittest.main()
