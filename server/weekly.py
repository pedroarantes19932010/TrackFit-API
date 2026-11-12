"""Agenda de fichas e acompanhamento de treinos na semana do piloto (UTC-3)."""
from datetime import date, datetime, time, timedelta, timezone

from fastapi import Depends, HTTPException
from server.models import Strict

ZONE = timezone(timedelta(hours=-3))
SCHEMA = """
CREATE TABLE IF NOT EXISTS scheduled_workouts(
 plan TEXT NOT NULL REFERENCES plans(id), scheduled_date TEXT NOT NULL, PRIMARY KEY(plan,scheduled_date));
CREATE INDEX IF NOT EXISTS sessions_week ON training_sessions(student,created);
"""


class Appointment(Strict):
    day: date
    scheduled: bool


def install(app, db, auth, trainer, get_plan):
    @app.post("/plans/{plan_id}/schedule")
    def schedule(plan_id: str, body: Appointment, user=Depends(trainer)):
        with db(True) as conn:
            plan = get_plan(conn, plan_id, user)
            if not conn.execute("SELECT 1 FROM trainer_students WHERE trainer_id=? AND student_id=?",
                                (user["id"],plan["student"])).fetchone():
                raise HTTPException(404, "Vínculo indisponível.")
            key = (plan_id,body.day.isoformat())
            if body.scheduled:
                if plan["state"] not in ("released","reviewed"):
                    raise HTTPException(409, "Somente fichas liberadas podem ser agendadas.")
                conn.execute("INSERT OR IGNORE INTO scheduled_workouts VALUES(?,?)",key)
            else:
                conn.execute("DELETE FROM scheduled_workouts WHERE plan=? AND scheduled_date=?",key)
        return {"ok":True}

    @app.get("/week/{offset}")
    def week(offset: int, user=Depends(auth)):
        if abs(offset)>52:
            raise HTTPException(422,"Escolha uma semana dentro de um ano.")
        today=datetime.now(ZONE).date()
        start=today+timedelta(days=7*offset-today.weekday())
        end=start+timedelta(days=7)
        owner = "t.trainer_id" if user["role"]=="trainer" else "t.student_id"
        with db() as conn:
            conn.execute("BEGIN")
            students={r["id"]:dict(r,completed=0,appointments=[],awaiting=[]) for r in conn.execute(
                f"""SELECT u.user_id AS id,COALESCE(n.name,u.username) AS name FROM trainer_students t
                    JOIN users u ON u.user_id=t.student_id LEFT JOIN mobile_names n ON n.user_id=u.user_id
                    WHERE {owner}=? ORDER BY name,u.user_id""",(user["id"],))}
            linked=f""" JOIN plans p ON p.id=x.plan JOIN trainer_students t ON t.trainer_id=p.trainer
                        AND t.student_id=p.student WHERE {owner}=? """
            finished=set()
            for r in conn.execute("SELECT p.student,x.plan,x.created FROM training_sessions x"+linked+
                    "AND x.state='finished' AND x.student=p.student AND x.created>=? AND x.created<?",
                    (user["id"],datetime.combine(start,time.min,ZONE).timestamp(),datetime.combine(end,time.min,ZONE).timestamp())):
                students[r["student"]]["completed"]+=1
                finished.add((r["plan"],datetime.fromtimestamp(r["created"],ZONE).date().isoformat()))
            for r in conn.execute("SELECT p.student,p.state,x.plan,x.scheduled_date FROM scheduled_workouts x"+linked+
                    "AND x.scheduled_date>=? AND x.scheduled_date<? ORDER BY x.scheduled_date,x.plan",
                    (user["id"],start.isoformat(),end.isoformat())):
                students[r["student"]]["appointments"].append({"plan":r["plan"],"date":r["scheduled_date"],
                    "done":(r["plan"],r["scheduled_date"]) in finished,"suspended":r["state"]=="suspended"})
            if user["role"]=="trainer":
                for r in conn.execute("SELECT p.student,x.plan FROM support_messages x"+linked+
                        "AND x.role='student' AND x.seq=(SELECT MAX(seq) FROM support_messages WHERE plan=x.plan) ORDER BY x.seq",
                        (user["id"],)):
                    students[r["student"]]["awaiting"].append(r["plan"])
        return {"start":start,"end":end-timedelta(days=1),"today":today,"students":list(students.values())}
