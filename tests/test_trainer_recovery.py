import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from server.app import create_app
from server.bootstrap import trainer_code


class TrainerRecovery(unittest.TestCase):
    def test_renew_preserves_identity_student_and_workout(self):
        with tempfile.TemporaryDirectory() as folder:
            app = create_app(Path(folder) / 'pilot.sqlite3', 'demo')
            old = {'Authorization': 'Bearer ' + trainer_code(app, 'Pedro')}
            with TestClient(app) as client:
                trainer = client.get('/me', headers=old).json()
                student = client.post('/students', headers=old, json={'name':'Teste'}).json()
                student_headers = {'Authorization':'Bearer '+student['access_code']}
                response = client.post('/v1/workouts', headers=old, json={
                    'student_id':student['id'],'exercises':[{'name':'Teste','sets':1,'reps':10,'rest_seconds':60}]})
                self.assertEqual(response.status_code,201)
                path = '/v1/workouts/' + response.json()['workout_id']
                with app.state.db(True) as db:
                    db.execute("INSERT INTO push_devices VALUES('device',?,'binding',9999999999)",(trainer['id'],))
                    db.execute("INSERT INTO push_jobs(event,binding) VALUES('event','binding')")
                renewed = {'Authorization':'Bearer '+trainer_code(app, None, renew=True)}
                self.assertEqual(client.get('/me',headers=old).status_code,401)
                self.assertEqual(client.get('/me',headers=renewed).json(),trainer)
                self.assertEqual(client.get(path,headers=student_headers).status_code,200)
                self.assertEqual(client.get(path,headers=renewed).status_code,200)
                with app.state.db() as db:
                    self.assertEqual(db.execute('SELECT count(*) FROM push_devices').fetchone()[0],0)
                    self.assertEqual(db.execute('SELECT count(*) FROM push_jobs').fetchone()[0],0)

    def test_expired_code_is_recoverable_and_does_not_duplicate_trainer(self):
        with tempfile.TemporaryDirectory() as folder:
            app = create_app(Path(folder)/'pilot.sqlite3','demo')
            with self.assertRaises(ValueError):
                trainer_code(app,None,renew=True)
            trainer_code(app,'Pedro')
            with app.state.db(True) as db:
                db.execute("UPDATE sessions SET expires_at='2000-01-01T00:00:00+00:00'")
            new = trainer_code(app,None,renew=True)
            with TestClient(app) as client:
                self.assertEqual(client.get('/me',headers={'Authorization':'Bearer '+new}).status_code,200)
            with app.state.db() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0],1)
