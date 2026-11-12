import tempfile
import time
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from server.accounts import add_code_account
from server.app import create_app, digest
from test_android_api import PROFILE, TEMPLATE, DAY


class IntegratedCatalogSupport(unittest.TestCase):
    def test_reference_generation_conversation_and_access(self):
        with tempfile.TemporaryDirectory() as root:
            app=create_app(Path(root)/'test.db','demo')
            with app.state.db(True) as db:
                for name, role in [('t','trainer'),('s','student'),('outsider','student')]:
                    add_code_account(db,name,name,role,'t',digest(name),time.time()+300)
            def auth(s): return {'Authorization':'Bearer '+s}
            with TestClient(app) as c:
                entry=c.get('/v1/exercises/seated_row').json()
                exercise=DAY['exercises'][0]|{'exercise_id':entry['exercise_id'],'name':entry['name']}
                template=TEMPLATE|{'days':[DAY|{'exercises':[exercise]}]}
                tid=c.post('/templates',headers=auth('t'),json=template).json()['id']
                c.post('/templates/'+tid+'/approval',headers=auth('t'),json={'approved':True})
                plan=c.post('/plans',headers=auth('s'),json={'request_id':str(uuid4()),'profile':PROFILE}).json()
                self.assertEqual(plan['days'][0]['exercises'][0]['exercise_id'],'seated_row')
                path='/plans/'+plan['id']+'/support'
                ask={'request_id':str(uuid4()),'message':'Qual aparelho usar?'}
                for _ in range(2): self.assertEqual(c.post(path,headers=auth('s'),json=ask).status_code,200)
                self.assertEqual(c.get('/support',headers=auth('t')).json()[0]['role'],'student')
                self.assertEqual(c.post(path,headers=auth('t'),json={'request_id':str(uuid4()),'message':'Veja a referência na ficha.'}).status_code,200)
                self.assertEqual([r['role'] for r in c.get(path,headers=auth('s')).json()],['student','trainer'])
                self.assertEqual(c.get(path,headers=auth('outsider')).status_code,404)
                self.assertEqual(c.post(path,headers=auth('outsider'),json=ask).status_code,404)
                self.assertEqual(c.get('/support',headers=auth('outsider')).json(),[])
                template['days'][0]['exercises'][0]['exercise_id']='unknown'
                self.assertEqual(c.post('/templates',headers=auth('t'),json=template).status_code,422)
