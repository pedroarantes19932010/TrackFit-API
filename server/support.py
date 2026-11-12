"""Uma conversa por ficha, restrita ao aluno e ao treinador responsável."""
import time
from uuid import UUID, uuid4
from server.push import enqueue
from fastapi import Depends, HTTPException
from pydantic import Field
from server.models import Strict

SCHEMA = """
CREATE TABLE IF NOT EXISTS support_messages(
 seq INTEGER PRIMARY KEY, plan TEXT NOT NULL REFERENCES plans(id),
 sender TEXT NOT NULL, role TEXT NOT NULL, version INTEGER NOT NULL,
 request_id TEXT NOT NULL, message TEXT NOT NULL, created REAL NOT NULL,
 UNIQUE(sender,request_id));
CREATE TABLE IF NOT EXISTS support_alerts(event TEXT PRIMARY KEY REFERENCES notifications(id));
CREATE INDEX IF NOT EXISTS support_plan ON support_messages(plan,seq);
"""

class Message(Strict):
    request_id: UUID
    message: str = Field(min_length=1,max_length=1200)


def install(app, db, authenticate, get_plan):
    def allowed(conn,plan_id,user):
        plan=get_plan(conn,plan_id,user)
        if not conn.execute("SELECT 1 FROM trainer_students WHERE trainer_id=? AND student_id=?",
                            (plan["trainer"],plan["student"])).fetchone():
            raise HTTPException(404,"Conversa indisponível.")
        return plan

    @app.get("/support")
    def inbox(user=Depends(authenticate)):
        owner="p.trainer" if user["role"]=="trainer" else "p.student"
        with db() as conn:
            rows=conn.execute(f"""SELECT m.plan,m.role,m.version,m.created,
                COALESCE(n.name,u.username) AS student_name
                FROM support_messages m JOIN plans p ON p.id=m.plan
                JOIN trainer_students t ON t.trainer_id=p.trainer AND t.student_id=p.student
                JOIN users u ON u.user_id=p.student LEFT JOIN mobile_names n ON n.user_id=p.student
                WHERE {owner}=? AND m.seq=(SELECT MAX(seq) FROM support_messages WHERE plan=m.plan)
                ORDER BY m.seq DESC""",(user["id"],))
            return [dict(row) for row in rows]

    @app.get("/plans/{plan_id}/support")
    def messages(plan_id: str,user=Depends(authenticate)):
        with db(True) as conn:
            allowed(conn,plan_id,user)
            conn.execute("UPDATE notifications SET seen=1 WHERE plan=? AND trainer=? AND id IN (SELECT event FROM support_alerts)",(plan_id,user["id"]))
            return [dict(r) for r in conn.execute("SELECT role,version,message,created FROM support_messages WHERE plan=? ORDER BY seq",(plan_id,))]

    @app.post("/plans/{plan_id}/support")
    def send(plan_id: str,body: Message,user=Depends(authenticate)):
        with db(True) as conn:
            plan=allowed(conn,plan_id,user)
            identity=(user["id"],str(body.request_id))
            old=conn.execute("SELECT plan,message FROM support_messages WHERE sender=? AND request_id=?",identity).fetchone()
            if old:
                if tuple(old)!=(plan_id,body.message):
                    raise HTTPException(409,"Mensagem já utilizada em outro envio.")
                return {"ok":True}
            conn.execute("""INSERT INTO support_messages(plan,sender,role,version,request_id,message,created)
                         VALUES(?,?,?,?,?,?,?)""",(plan_id,user["id"],user["role"],plan["version"],str(body.request_id),body.message,time.time()))
            recipient = plan["trainer"] if user["role"] == "student" else plan["student"]
            event = str(uuid4())
            conn.execute("INSERT INTO notifications VALUES(?,?,?,?,?,0)",
                         (event,recipient,plan_id,"Nova mensagem no suporte da ficha.",time.time()))
            conn.execute("INSERT INTO support_alerts VALUES(?)",(event,))
            enqueue(conn,event,recipient)
        return {"ok":True}
