import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
import httpx
from fastapi.testclient import TestClient
from server.accounts import add_code_account
from server.app import create_app, digest
from server.provider import choose_template, ProviderError
from server.push import Device, register, deliver_one, RemovedToken
from test_android_api import TEMPLATE, PROFILE


class PilotDelivery(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.app=create_app(Path(folder.name)/"test.sqlite3","demo")
        self.client=TestClient(self.app)
        self.addCleanup(self.client.close)
        self.trainer={"Authorization":"Bearer trainer"}
        self.student={"Authorization":"Bearer student"}
        with self.app.state.db(True) as db:
            for name,role,trainer in [("trainer","trainer","trainer"),("student","student","trainer"),("other","trainer","other")]:
                add_code_account(db,name,name,role,trainer,digest(name),time.time()+3600)
            register(db,"trainer",Device(token="fictitious-device-token",binding=str(uuid4())),time.time()+3600)
        result=self.client.post("/templates",headers=self.trainer,json=TEMPLATE)
        self.client.post("/templates/"+result.json()["id"]+"/approval",headers=self.trainer,json={"approved":True})

    def generate(self,**overrides):
        return self.client.post("/plans",headers=self.student,json={"request_id":str(uuid4()),"profile":PROFILE|overrides}).json()

    def test_one_push_per_complete_plan_and_device(self):
        self.generate(needs_review=True)
        self.assertFalse(deliver_one(self.app.state.db,self.fail))
        self.generate()
        calls=[]
        self.assertTrue(deliver_one(self.app.state.db,lambda *args:calls.append(args)))
        self.assertFalse(deliver_one(self.app.state.db,self.fail))
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][0],"fictitious-device-token")

    def test_retry_and_invalid_token(self):
        self.generate()
        def fail(*args): raise OSError("temporário")
        deliver_one(self.app.state.db,fail)
        with self.app.state.db(True) as db:
            row=db.execute("SELECT attempts,available FROM push_jobs").fetchone()
            self.assertEqual(row[0],1)
            self.assertGreater(row[1],time.time())
            db.execute("UPDATE push_jobs SET available=0")
        def invalid(*args): raise RemovedToken()
        deliver_one(self.app.state.db,invalid)
        with self.app.state.db() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM push_devices").fetchone()[0],0)

    def test_read_or_expired_alert_is_not_sent(self):
        self.generate()
        row=self.client.get("/notifications",headers=self.trainer).json()[0]
        self.client.post(f"/notifications/{row['id']}/read",headers=self.trainer)
        self.assertFalse(deliver_one(self.app.state.db,self.fail))
        self.generate()
        with self.app.state.db(True) as db: db.execute("UPDATE push_devices SET expires=0")
        self.assertFalse(deliver_one(self.app.state.db,self.fail))

    def test_history_of_both_formats_and_performed_sets(self):
        plan=self.generate()
        legacy=self.client.post("/v1/workouts",headers=self.trainer,json={"student_id":"student","exercises":[{"name":"Exemplo","sets":1,"reps":2,"rest_seconds":60}]})
        self.assertEqual(legacy.status_code,201,legacy.text)
        session=self.client.post(f"/plans/{plan['id']}/sessions",headers=self.student,json={"expected_version":1,"request_id":str(uuid4()),"day":0}).json()
        self.client.post(f"/sessions/{session['id']}/finish",headers=self.student,json={"sets":[{"exercise_index":0,"set_index":0,"weight_kg":12.5,"reps":10}],"note":"feito"})
        for headers in [self.student,self.trainer]:
            rows=self.client.get("/history/page/0",headers=headers).json()
            self.assertEqual({r['kind'] for r in rows},{"sessao","ficha_v1","plano"})
            actual=next(r for r in rows if r['kind']=="sessao")['payload']['actual']
            self.assertEqual(actual['sets'][0]['weight_kg'],12.5)
        self.assertEqual(self.client.get("/history",headers={"Authorization":"Bearer other"}).json(),[])

    def test_student_push_requires_configured_service(self):
        res=self.client.post("/push/devices",headers=self.student,json={"binding":str(uuid4()),"token":"another-fictitious-device"})
        self.assertEqual(res.status_code,503)

    def test_support_recipient_and_retry(self):
        path = "/plans/"+self.generate()["id"]+"/support"
        for author, reader in [(self.student,self.trainer),(self.trainer,self.student)]:
            body = {"message":"Mensagem de teste","request_id":str(uuid4())}
            for _ in range(2):
                self.assertEqual(self.client.post(path,headers=author,json=body).status_code,200)
            def alerts():
                return [n for n in self.client.get("/notifications",headers=reader).json() if n["kind"]=="support"]
            self.assertEqual([n["seen"] for n in alerts()],[0])
            self.assertEqual(self.client.get(path,headers=reader).status_code,200)
            self.assertEqual([n["seen"] for n in alerts()],[1])

    def test_curated_videos_by_trainer(self):
        path="/catalog/seated_row/videos"
        video={"kind":"tips","creator_name":"Canal teste","youtube_id":"abc_DEF-123"}
        def videos(headers):
            return next(e for e in self.client.get("/catalog",headers=headers).json() if e["exercise_id"]=="seated_row")["videos"]
        self.assertEqual(self.client.post(path,headers=self.student,json=video).status_code,403)
        self.assertEqual(self.client.post(path,headers=self.trainer,json=video|{"youtube_id":"invalid"}).status_code,422)
        for _ in range(2):
            self.assertEqual(self.client.post(path,headers=self.trainer,json=video).status_code,200)
        self.assertEqual(videos(self.student),[video])
        self.assertEqual(videos({"Authorization":"Bearer other"}),[])
        self.assertEqual(self.client.post(path+"/abc_DEF-123/remove",headers=self.trainer).status_code,200)
        self.assertEqual(videos(self.student),[])


class AIContract(unittest.TestCase):
    def call(self, reply):
        sent=[]
        def transport(req):
            sent.append(req.content.decode())
            return httpx.Response(200,json=reply)
        client=httpx.Client(transport=httpx.MockTransport(transport))
        with patch.dict(os.environ,{"OPENAI_API_KEY":"test-only","OPENAI_MODEL":"test-model"}),patch('server.provider.httpx.Client',return_value=client):
            result=choose_template(PROFILE|{'limitations':'private-text'},[{'id':'allowed','data':TEMPLATE}],'openai')
        import json
        supplied=json.loads(json.loads(sent[0])["input"])
        self.assertEqual(supplied["minutos_disponiveis"],PROFILE["minutes"])
        self.assertEqual(supplied["fichas"][0]["minutos_previstos"],TEMPLATE["minutes"])
        self.assertNotIn('private-text',sent[0])
        return result

    def test_valid_selection(self):
        self.assertEqual(self.call({'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'{"template_id":"allowed"}'}]}]}),'allowed')

    def test_invalid_refused_incomplete_and_unknown(self):
        for reply in [[],{'status':'incomplete'},{'status':'completed','output':[{'type':'message','content':[{'type':'refusal'}]}]},
                      {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'{"template_id":"inventado"}'}]}]}]:
            with self.subTest(reply=reply),self.assertRaises(ProviderError):
                self.call(reply)
