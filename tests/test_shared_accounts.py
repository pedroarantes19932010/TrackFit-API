import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from server.accounts import add_code_account
from server.app import create_app, digest
from trackfit_api.identity import hash_password


class SharedAccountsTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "trackfit.db"

    def test_android_registration_works_in_v1_and_other_students_cannot_read(self):
        app = create_app(self.path)
        with app.state.db(True) as db:
            add_code_account(db, "prof", "Pedro", "trainer", "prof", digest("private-test-code"), time.time()+3600)
        trainer = {"Authorization": "Bearer private-test-code"}
        with TestClient(app) as client:
            def register(name):
                response = client.post("/students", headers=trainer, json={"name": name})
                self.assertEqual(response.status_code, 201)
                data = response.json()
                return data["id"], {"Authorization": "Bearer " + data["access_code"]}
            student, first = register("Fictício A")
            _, second = register("Fictício B")
            self.assertEqual(client.get("/v1/auth/me", headers=first).json()["user_id"], student)
            response = client.post("/v1/workouts", headers=trainer, json={
                "student_id": student, "exercises": [{"name":"Exemplo","sets":1,"reps":1,"rest_seconds":60}]})
            self.assertEqual(response.status_code, 201)
            path = "/v1/workouts/" + response.json()["workout_id"]
            self.assertEqual(client.get(path, headers=first).status_code, 200)
            self.assertEqual(client.get(path, headers=second).status_code, 403)

    def test_v1_login_enters_mobile_with_same_id(self):
        app = create_app(self.path)
        with app.state.db(True) as db:
            db.execute("INSERT INTO users VALUES(?,?,?,?)", ("t","prof","trainer",hash_password("password-for-test")))
            db.execute("INSERT INTO users VALUES(?,?,?,?)", ("s","aluno","student",hash_password("password-for-test")))
            db.execute("INSERT INTO trainer_students VALUES(?,?)", ("t","s"))
        with TestClient(app) as client:
            login = client.post("/v1/auth/login", json={"username":"aluno","password":"password-for-test"})
            self.assertEqual(login.status_code, 200)
            result = client.get("/me", headers={"Authorization":"Bearer "+login.json()["access_token"]})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["id"], "s")

    def test_old_codes_and_recorded_session_survive_two_startups(self):
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE users(id TEXT PRIMARY KEY,name TEXT,role TEXT,trainer TEXT,token_hash TEXT,expires REAL)")
            db.execute("CREATE TABLE sessions(id TEXT PRIMARY KEY,student TEXT,plan TEXT,version INTEGER,day INTEGER,snapshot TEXT,state TEXT,actual TEXT,request_id TEXT,created REAL)")
            for user,role,expiry in (("t","trainer",time.time()+60),("s","student",time.time()+60),("old","student",0)):
                db.execute("INSERT INTO users VALUES(?,?,?,?,?,?)", (user,user,role,"t",digest(user),expiry))
            db.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?,?)", ("x","s","p",1,0,'{"title":"Original"}',"finished",'{"sets":[]}','req',0))
        for _ in range(2):
            with TestClient(create_app(self.path)) as client:
                self.assertEqual(client.get("/v1/auth/me", headers={"Authorization":"Bearer s"}).json()["user_id"],"s")
                result = client.get("/sessions", headers={"Authorization":"Bearer s"}).json()
                self.assertEqual([(x["id"],x["snapshot"]["title"]) for x in result], [("x","Original")])
                self.assertEqual(client.get("/me", headers={"Authorization":"Bearer old"}).status_code,401)
