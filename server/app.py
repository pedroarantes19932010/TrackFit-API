"""Servidor do piloto TrackFit: SQLite, códigos de acesso e fichas versionadas."""
import hashlib
import json
import os
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from trackfit_api.identity import current_user, request_database
from trackfit_api.auth_routes import router as auth_router
from trackfit_api.workout_routes import router as workout_router
from server import push, timeline, support, videos
from trackfit_api.catalog_routes import router as catalog_router
from datetime import datetime
from server.accounts import add_code_account, prepare_accounts
from server.models import (Generate, Review, Template, TemplateApproval, NewStudent, Start, Finish)
from server.provider import choose_template, ProviderError


def uid():
    return str(uuid.uuid4())


def packed(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


SCHEMA = """
CREATE TABLE IF NOT EXISTS templates(id TEXT PRIMARY KEY,trainer TEXT NOT NULL,data TEXT NOT NULL,approved INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS plans(id TEXT PRIMARY KEY,student TEXT NOT NULL,trainer TEXT NOT NULL,request_id TEXT NOT NULL,request_hash TEXT NOT NULL,profile TEXT NOT NULL,version INTEGER NOT NULL,state TEXT NOT NULL,source TEXT NOT NULL,template_id TEXT,created REAL NOT NULL,UNIQUE(student,request_id));
CREATE TABLE IF NOT EXISTS versions(plan TEXT NOT NULL,version INTEGER NOT NULL,data TEXT NOT NULL,note TEXT NOT NULL,created REAL NOT NULL,PRIMARY KEY(plan,version));
CREATE TABLE IF NOT EXISTS notifications(id TEXT PRIMARY KEY,trainer TEXT NOT NULL,plan TEXT NOT NULL,message TEXT NOT NULL,created REAL NOT NULL,seen INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS training_sessions(id TEXT PRIMARY KEY,student TEXT NOT NULL,plan TEXT NOT NULL,version INTEGER NOT NULL,day INTEGER NOT NULL,snapshot TEXT NOT NULL,state TEXT NOT NULL,actual TEXT,request_id TEXT NOT NULL,created REAL NOT NULL,UNIQUE(student,request_id));
CREATE TABLE IF NOT EXISTS rate_events(student TEXT NOT NULL,created REAL NOT NULL);
"""


def create_app(db_path=None, mode=None, chooser=None):
    pilot_path, api_path = os.getenv("TRACKFIT_DB"), os.getenv("TRACKFIT_DB_PATH")
    if not db_path and pilot_path and api_path and Path(pilot_path).resolve() != Path(api_path).resolve():
        raise ValueError("Há dois bancos configurados. Escolha explicitamente um banco para o serviço integrado.")
    path = Path(db_path or api_path or pilot_path or "data/trackfit.sqlite3").resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    provider_mode = mode or os.getenv("TRACKFIT_PROVIDER", "demo")
    selector = chooser or choose_template

    @contextmanager
    def db(write=False):
        conn = sqlite3.connect(path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            if write:
                conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    with db(True) as conn:
        prepare_accounts(conn)
        for statement in (SCHEMA + push.SCHEMA + support.SCHEMA + videos.SCHEMA).split(";"):
            if statement.strip():
                conn.execute(statement)
    push_enabled = os.getenv("TRACKFIT_PUSH") == "fcm"
    app = FastAPI(title="TrackFit — piloto", version="0.4.0", lifespan=push.worker_lifespan(db,push_enabled))
    app.state.db = db

    app.include_router(catalog_router)
    app.include_router(auth_router)
    app.include_router(workout_router)

    @app.middleware("http")
    async def bind_database(request, call_next):
        binding = request_database.set(path)
        try:
            return await call_next(request)
        finally:
            request_database.reset(binding)

    def auth(identity=Depends(current_user)):
        user_id, role = identity["user_id"], identity["role"]
        with db() as conn:
            name = conn.execute(
                "SELECT COALESCE(n.name,u.username) FROM users u LEFT JOIN mobile_names n USING(user_id) WHERE u.user_id=?",
                (user_id,),
            ).fetchone()[0]
            trainer_id = user_id
            if role == "student":
                links = conn.execute("SELECT trainer_id FROM trainer_students WHERE student_id=?", (user_id,)).fetchall()
                if len(links) != 1:
                    raise HTTPException(409, "Para usar o piloto, o aluno precisa de um treinador responsável definido.")
                trainer_id = links[0][0]
        return {"id": user_id, "role": role, "name": name, "trainer": trainer_id}

    def trainer(user=Depends(auth)):
        if user["role"] != "trainer":
            raise HTTPException(403, "Área exclusiva do treinador.")
        return user

    def student(user=Depends(auth)):
        if user["role"] != "student":
            raise HTTPException(403, "Use um acesso de aluno.")
        return user

    def get_plan(conn, plan_id, user):
        plan = conn.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
        if plan is None or (user["role"] == "student" and plan["student"] != user["id"]) or (user["role"] == "trainer" and plan["trainer"] != user["id"]):
            raise HTTPException(404, "Ficha não encontrada.")
        return dict(plan)

    def show_plan(conn, plan, user):
        out = dict(plan)
        version = conn.execute("SELECT * FROM versions WHERE plan=? AND version=?", (plan["id"], plan["version"])).fetchone()
        data = json.loads(version["data"])
        out["days"] = data if user["role"] == "trainer" or plan["state"] in ("released", "reviewed") else []
        out["profile"] = json.loads(plan["profile"])
        out["note"] = version["note"]
        out["student_name"] = conn.execute("SELECT COALESCE(n.name,u.username) FROM users u LEFT JOIN mobile_names n USING(user_id) WHERE u.user_id=?", (plan["student"],)).fetchone()[0]
        out.pop("request_hash", None)
        return out

    def notify(conn, plan, message, complete=False):
        event = uid()
        conn.execute("INSERT INTO notifications VALUES(?,?,?,?,?,0)", (event, plan["trainer"], plan["id"], message, time.time()))
        if complete:
            push.enqueue(conn,event,plan["trainer"])

    @app.get("/health")
    def health():
        return {"status": "ok", "provider": provider_mode, "pilot": True}

    @app.get("/me")
    def me(user=Depends(auth)):
        return {"id": user["id"], "name": user["name"], "role": user["role"], "provider": provider_mode}

    @app.post("/students", status_code=201)
    def add_student(body: NewStudent, user=Depends(trainer)):
        token, student_id = secrets.token_urlsafe(32), uid()
        with db(True) as conn:
            add_code_account(conn, student_id, body.name, "student", user["id"], digest(token), time.time() + 30 * 86400)
        return {"id": student_id, "name": body.name, "access_code": token, "expires_in_days": 30}

    @app.get("/templates")
    def templates(user=Depends(trainer)):
        with db() as conn:
            return [{"id": r["id"], "approved": bool(r["approved"]), "data": json.loads(r["data"])} for r in conn.execute("SELECT * FROM templates WHERE trainer=?", (user["id"],))]

    @app.post("/templates", status_code=201)
    def create_template(body: Template, user=Depends(trainer)):
        if body.min_age > body.max_age:
            raise HTTPException(422, "Faixa de idade inválida.")
        template_id = uid()
        with db(True) as conn:
            conn.execute("INSERT INTO templates VALUES(?,?,?,0)", (template_id, user["id"], packed(body.model_dump(exclude_none=True))))
        return {"id": template_id, "approved": False}

    @app.post("/templates/{template_id}/approval")
    def approve_template(template_id: str, body: TemplateApproval, user=Depends(trainer)):
        with db(True) as conn:
            result = conn.execute("UPDATE templates SET approved=? WHERE id=? AND trainer=?", (int(body.approved), template_id, user["id"]))
            if result.rowcount != 1:
                raise HTTPException(404, "Modelo não encontrado.")
        return {"approved": body.approved}

    @app.post("/plans", status_code=201)
    def generate(body: Generate, user=Depends(student)):
        payload_hash = digest(packed(body.profile.model_dump()))
        profile = body.profile.model_dump()
        # Reservation limits cost even for failures; no database lock during network calls.
        with db(True) as conn:
            existing = conn.execute("SELECT * FROM plans WHERE student=? AND request_id=?", (user["id"], body.request_id)).fetchone()
            if existing:
                if existing["request_hash"] != payload_hash:
                    raise HTTPException(409, "Identificador já utilizado com outra avaliação.")
                return show_plan(conn, existing, user)
            conn.execute("DELETE FROM rate_events WHERE created<?", (time.time()-3600,))
            if conn.execute("SELECT count(*) FROM rate_events WHERE student=?", (user["id"],)).fetchone()[0] >= 5:
                raise HTTPException(429, "Limite de 5 solicitações por hora. Aguarde para tentar novamente.")
            conn.execute("INSERT INTO rate_events VALUES(?,?)", (user["id"], time.time()))
            candidates = []
            for row in conn.execute("SELECT * FROM templates WHERE trainer=? AND approved=1", (user["trainer"],)):
                t = json.loads(row["data"])
                if (all(t[k] == profile[k] for k in ("goal", "experience", "equipment")) and len(t["days"]) == profile["days"] and t["minutes"] <= profile["minutes"] and t["min_age"] <= profile["age"] <= t["max_age"]):
                    candidates.append({"id": row["id"], "data": t})
        blocked = profile["needs_review"] or bool(profile["limitations"].strip())
        chosen, days, state = None, [], "pending"
        note = "Avaliação individual necessária antes de liberar a ficha." if blocked else "Nenhum modelo aprovado compatível. Aguardando treinador."
        if candidates and not blocked:
            try:
                selected_id = selector(profile, candidates, provider_mode)
                chosen = next(c for c in candidates if c["id"] == selected_id)
            except (ProviderError, StopIteration):
                raise HTTPException(503, "Não foi possível gerar a ficha. Nenhuma ficha foi liberada; tente novamente.")
            days, state = chosen["data"]["days"], "released"
            note = "Gerada por IA — revisão do treinador pendente." if provider_mode == "openai" else "DEMONSTRAÇÃO: seleção por regras, sem IA — revisão pendente."
        with db(True) as conn:
            # Recheck approval after the provider returns: revocation wins the race.
            if chosen:
                current = conn.execute("SELECT approved FROM templates WHERE id=?", (chosen["id"],)).fetchone()
                if not current or not current[0]:
                    raise HTTPException(409, "Modelo retirado pelo treinador. Solicite nova avaliação.")
            existing = conn.execute("SELECT * FROM plans WHERE student=? AND request_id=?", (user["id"], body.request_id)).fetchone()
            if existing:
                if existing["request_hash"] != payload_hash:
                    raise HTTPException(409, "Solicitação conflitante.")
                return show_plan(conn, existing, user)
            plan_id = uid()
            conn.execute("INSERT INTO plans VALUES(?,?,?,?,?,?,?,?,?,?,?)", (plan_id,user["id"],user["trainer"],body.request_id,payload_hash,packed(profile),1,state,provider_mode,chosen["id"] if chosen else None,time.time()))
            conn.execute("INSERT INTO versions VALUES(?,?,?,?,?)", (plan_id,1,packed(days),note,time.time()))
            plan = get_plan(conn, plan_id, user)
            notify(conn, plan, "Ficha completa gerada para revisão." if days else "Avaliação aguardando atendimento antes de gerar ficha.", complete=bool(days))
            return show_plan(conn, plan, user)

    @app.get("/plans")
    def plans(user=Depends(auth)):
        field = "trainer" if user["role"] == "trainer" else "student"
        with db() as conn:
            return [show_plan(conn, r, user) for r in conn.execute(f"SELECT * FROM plans WHERE {field}=? ORDER BY created DESC LIMIT 100", (user["id"],))]

    @app.get("/plans/{plan_id}")
    def plan_detail(plan_id: str, user=Depends(auth)):
        with db() as conn:
            return show_plan(conn, get_plan(conn, plan_id, user), user)

    @app.post("/plans/{plan_id}/review")
    def review(plan_id: str, body: Review, user=Depends(trainer)):
        with db(True) as conn:
            plan = get_plan(conn, plan_id, user)
            if plan["version"] != body.expected_version:
                raise HTTPException(409, "A ficha mudou. Atualize antes de revisar.")
            days = json.loads(conn.execute("SELECT data FROM versions WHERE plan=? AND version=?", (plan_id,plan["version"])).fetchone()[0])
            if body.action == "edit":
                if not body.days:
                    raise HTTPException(422, "Informe a ficha completa revisada.")
                days = [d.model_dump(exclude_none=True) for d in body.days]
                if len(days) != json.loads(plan["profile"])["days"]:
                    raise HTTPException(422, "A quantidade de dias deve corresponder à avaliação.")
            elif body.days is not None:
                raise HTTPException(422, "Para alterar exercícios, use editar.")
            if body.action != "suspend" and not days:
                raise HTTPException(422, "Adicione exercícios antes de aprovar.")
            version = plan["version"]+1
            state = "suspended" if body.action == "suspend" else "reviewed"
            conn.execute("INSERT INTO versions VALUES(?,?,?,?,?)", (plan_id,version,packed(days),body.note,time.time()))
            conn.execute("UPDATE plans SET version=?,state=? WHERE id=?", (version,state,plan_id))
            # Safety suspension immediately stops active sessions; normal edits do not alter snapshots.
            if state == "suspended":
                conn.execute("UPDATE training_sessions SET state='suspended' WHERE plan=? AND state='active'", (plan_id,))
            return show_plan(conn, get_plan(conn, plan_id, user), user)

    @app.get("/history")
    def unified_history(offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100), user=Depends(auth)):
        with db() as conn:
            return timeline.history(conn,user,offset,limit)

    @app.get("/history/page/{page}")
    def history_page(page: int, user=Depends(auth)):
        if page < 0 or page > 100000:
            raise HTTPException(422, "Página inválida.")
        with db() as conn:
            return timeline.history(conn,user,30*page,30)

    @app.post("/push/devices")
    def register_device(body: push.Device, authorization: str = Header(), user=Depends(auth)):
        if not push_enabled:
            raise HTTPException(503, "Envio em segundo plano ainda não configurado no servidor.")
        with db(True) as conn:
            row = conn.execute("SELECT expires_at FROM sessions WHERE token_hash=? AND user_id=?",
                               (digest(authorization[7:]),user["id"])).fetchone()
            if not row:
                raise HTTPException(401, "Entre novamente.")
            push.register(conn,user["id"],body,datetime.fromisoformat(row[0]).timestamp())
        return {"ok":True}

    @app.get("/notifications")
    def notifications(user=Depends(auth)):
        with db() as conn:
            return [dict(r) for r in conn.execute("SELECT n.*, CASE WHEN s.event IS NULL THEN 'plan' ELSE 'support' END AS kind FROM notifications n JOIN plans p ON p.id=n.plan JOIN trainer_students t ON t.trainer_id=p.trainer AND t.student_id=p.student LEFT JOIN support_alerts s ON s.event=n.id WHERE n.trainer=? ORDER BY n.created DESC LIMIT 100", (user["id"],))]

    @app.post("/notifications/{notification_id}/read")
    def mark_read(notification_id: str, user=Depends(auth)):
        with db(True) as conn:
            if conn.execute("UPDATE notifications SET seen=1 WHERE id=? AND trainer=?", (notification_id,user["id"])).rowcount != 1:
                raise HTTPException(404, "Aviso não encontrado.")
        return {"ok": True}

    def show_session(row):
        result = dict(row)
        result["snapshot"] = json.loads(result["snapshot"])
        result["actual"] = json.loads(result["actual"]) if result["actual"] else None
        return result

    @app.get("/sessions")
    def sessions(user=Depends(student)):
        with db() as conn:
            return [show_session(r) for r in conn.execute("SELECT * FROM training_sessions WHERE student=? ORDER BY created DESC LIMIT 100", (user["id"],))]

    @app.post("/plans/{plan_id}/sessions", status_code=201)
    def start_session(plan_id: str, body: Start, user=Depends(student)):
        with db(True) as conn:
            plan = get_plan(conn, plan_id, user)
            old = conn.execute("SELECT * FROM training_sessions WHERE student=? AND request_id=?", (user["id"],body.request_id)).fetchone()
            if old:
                if old["plan"] != plan_id or old["version"] != body.expected_version or old["day"] != body.day:
                    raise HTTPException(409, "Solicitação conflitante.")
                return show_session(old)
            if plan["state"] not in ("released", "reviewed"):
                raise HTTPException(409, "Ficha ainda não liberada ou suspensa.")
            if plan["version"] != body.expected_version:
                raise HTTPException(409, "Existe uma nova versão. Atualize a ficha.")
            if conn.execute("SELECT id FROM training_sessions WHERE student=? AND state='active'", (user["id"],)).fetchone():
                raise HTTPException(409, "Você já tem um treino em andamento. Abra o histórico.")
            days = json.loads(conn.execute("SELECT data FROM versions WHERE plan=? AND version=?", (plan_id,plan["version"])).fetchone()[0])
            if body.day >= len(days):
                raise HTTPException(422, "Dia inválido.")
            session_id = uid()
            conn.execute("INSERT INTO training_sessions VALUES(?,?,?,?,?,?,?,?,?,?)", (session_id,user["id"],plan_id,plan["version"],body.day,packed(days[body.day]),"active",None,body.request_id,time.time()))
            return show_session(conn.execute("SELECT * FROM training_sessions WHERE id=?", (session_id,)).fetchone())

    @app.post("/sessions/{session_id}/finish")
    def finish(session_id: str, body: Finish, user=Depends(student)):
        with db(True) as conn:
            row = conn.execute("SELECT * FROM training_sessions WHERE id=? AND student=?", (session_id,user["id"])).fetchone()
            if not row:
                raise HTTPException(404, "Treino não encontrado.")
            actual = packed(body.model_dump(exclude_none=True))
            if row["state"] == "finished" and row["actual"] == actual:
                return show_session(row)
            if row["state"] != "active":
                raise HTTPException(409, "Treino encerrado ou suspenso. Os dados anteriores foram preservados.")
            exercises = json.loads(row["snapshot"])["exercises"]
            seen = set()
            for s in body.sets:
                pair = (s.exercise_index,s.set_index)
                if pair in seen or s.exercise_index >= len(exercises) or s.set_index >= exercises[s.exercise_index]["sets"]:
                    raise HTTPException(422, "Série inválida ou repetida.")
                seen.add(pair)
            conn.execute("UPDATE training_sessions SET state='finished',actual=? WHERE id=?", (actual,session_id))
            return show_session(conn.execute("SELECT * FROM training_sessions WHERE id=?", (session_id,)).fetchone())

    videos.install(app, db, auth, trainer)
    support.install(app, db, auth, get_plan)
    return app
