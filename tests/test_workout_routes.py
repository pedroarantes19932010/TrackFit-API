"""Smoke tests for authenticated workout routes."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from trackfit_api.identity import hash_password, identity_db
from trackfit_api.main import app


class WorkoutRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        env = patch.dict(os.environ, {"TRACKFIT_DB_PATH": str(Path(self.temp.name) / "db.sqlite")})
        env.start()
        self.addCleanup(env.stop)
        with identity_db() as db:
            db.execute("INSERT INTO users VALUES (?,?,?,?)", ("trainer1", "prof", "trainer", hash_password("senha-muito-forte-123")))
            db.execute("INSERT INTO users VALUES (?,?,?,?)", ("student1", "aluno", "student", hash_password("senha-muito-forte-456")))
            db.execute("INSERT INTO trainer_students VALUES (?,?)", ("trainer1", "student1"))
        self.client = TestClient(app)
        login = self.client.post("/v1/auth/login", json={"username": "prof", "password": "senha-muito-forte-123"})
        self.assertEqual(login.status_code, 200, login.text)
        self.headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        self.payload = {"student_id": "student1", "exercises": [{"name": "Remada", "sets": 3, "reps": 12, "rest_seconds": 60}]}

    def test_unauthenticated(self):
        self.assertEqual(self.client.post("/v1/workouts", json=self.payload).status_code, 401)
        self.assertEqual(self.client.get("/v1/workouts/unknown").status_code, 401)

    def test_publish_revise_and_history(self):
        created = self.client.post("/v1/workouts", json=self.payload, headers=self.headers)
        self.assertEqual(created.status_code, 201, created.text)
        wid = created.json()["workout_id"]
        self.assertEqual(self.client.get(f"/v1/workouts/{wid}", headers=self.headers).status_code, 200)
        revision = self.client.post(f"/v1/workouts/{wid}/revisions", headers=self.headers, json={
            "expected_version": 1, "exercises": self.payload["exercises"]})
        self.assertEqual(revision.status_code, 201, revision.text)
        self.assertEqual(revision.json()["reviewed_by"], "trainer1")
        versions = self.client.get(f"/v1/workouts/{wid}/versions", headers=self.headers)
        self.assertEqual([v["version"] for v in versions.json()], [1, 2])
        self.assertEqual(self.client.post(f"/v1/workouts/{wid}/revisions", headers=self.headers, json={
            "expected_version": 1, "exercises": self.payload["exercises"]}).status_code, 409)

    def test_invalid_input(self):
        self.assertEqual(self.client.post("/v1/workouts", json={**self.payload, "exercises": []}, headers=self.headers).status_code, 422)


if __name__ == "__main__":
    unittest.main()
