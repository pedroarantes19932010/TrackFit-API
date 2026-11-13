"""Fila persistente para avisos genéricos de ficha completa no Android."""
import os
import threading
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import HTTPException
import httpx
from pydantic import BaseModel, Field

SCHEMA = """
CREATE TABLE IF NOT EXISTS push_devices(
 token TEXT PRIMARY KEY, trainer TEXT NOT NULL, binding TEXT NOT NULL UNIQUE, expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS push_jobs(
 event TEXT NOT NULL, binding TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
 available REAL NOT NULL DEFAULT 0, lease TEXT, PRIMARY KEY(event,binding));
"""


class Device(BaseModel):
    token: str = Field(min_length=16, max_length=4096)
    binding: str = Field(pattern=r"^[0-9a-fA-F-]{36}$")


def register(conn, user, device, expiry):
    conn.execute("DELETE FROM push_devices WHERE expires<=?", (time.time(),))
    existing = conn.execute("SELECT binding FROM push_devices WHERE token=?", (device.token,)).fetchone()
    if not existing and conn.execute("SELECT count(*) FROM push_devices WHERE trainer=?", (user,)).fetchone()[0] >= 8:
        raise HTTPException(409, "Limite de aparelhos atingido.")
    conn.execute("""INSERT INTO push_devices VALUES(?,?,?,?) ON CONFLICT(token) DO UPDATE SET
                 trainer=excluded.trainer,binding=excluded.binding,expires=excluded.expires""",
                 (device.token, user, device.binding, expiry))


def enqueue(conn, event, trainer):
    conn.execute("""INSERT INTO push_jobs(event,binding)
                 SELECT ?,binding FROM push_devices WHERE trainer=? AND expires>?""",
                 (event, trainer, time.time()))


class RemovedToken(Exception):
    pass


class Sender:
    def __init__(self):
        import google.auth
        from google.auth.transport.requests import Request
        self.credentials, default_project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/firebase.messaging"])
        project = os.getenv("TRACKFIT_FIREBASE_PROJECT") or default_project
        if not project:
            raise ValueError("Configure TRACKFIT_FIREBASE_PROJECT.")
        self.url = f"https://fcm.googleapis.com/v1/projects/{project}/messages:send"
        self.refresh = Request()

    def __call__(self, token, binding, event):
        headers = {}
        self.credentials.before_request(self.refresh, "POST", self.url, headers)
        response = httpx.post(self.url, headers=headers, timeout=10, json={"message":{
            "token": token, "data": {"binding":binding,"event":event},
            "android":{"priority":"HIGH","ttl":"86400s"}}})
        if response.status_code == 404:
            details = response.json().get("error", {}).get("details", [])
            if any(item.get("errorCode") == "UNREGISTERED" for item in details):
                raise RemovedToken()
        response.raise_for_status()


def deliver_one(db, send):
    now = time.time()
    lease = str(uuid.uuid4())
    with db(True) as conn:
        conn.execute("DELETE FROM push_devices WHERE expires<=?", (now,))
        conn.execute("""DELETE FROM push_jobs WHERE binding NOT IN (SELECT binding FROM push_devices)
                      OR NOT EXISTS (
                      SELECT 1 FROM notifications n JOIN plans p ON p.id=n.plan
                      JOIN trainer_students t ON t.trainer_id=p.trainer AND t.student_id=p.student
                      JOIN push_devices d ON d.binding=push_jobs.binding AND d.trainer=n.trainer
                      WHERE n.id=push_jobs.event AND n.seen=0 AND n.created>?)""", (now-86400,))
        row = conn.execute("""SELECT j.event,j.binding,j.attempts,d.token FROM push_jobs j
            JOIN push_devices d USING(binding) WHERE available<=? ORDER BY available LIMIT 1""",(now,)).fetchone()
        if not row:
            return False
        event,binding,attempts,token = row
        conn.execute("UPDATE push_jobs SET available=?,lease=? WHERE event=? AND binding=?", (now+90,lease,event,binding))
    try:
        send(token,binding,event)
    except RemovedToken:
        with db(True) as conn:
            conn.execute("DELETE FROM push_devices WHERE binding=? AND token=?", (binding,token))
    except Exception:
        if attempts < 6:
            with db(True) as conn:
                conn.execute("""UPDATE push_jobs SET attempts=attempts+1,available=?,lease=NULL
                             WHERE event=? AND binding=? AND lease=?""",
                             (time.time()+min(3600,30*2**attempts),event,binding,lease))
            return True
    with db(True) as conn:
        conn.execute("DELETE FROM push_jobs WHERE event=? AND binding=? AND lease=?", (event,binding,lease))
    return True


def worker_lifespan(db, enabled):
    @asynccontextmanager
    async def lifespan(app):
        stop = threading.Event()
        if enabled:
            sender = Sender()
            def work():
                while not stop.is_set():
                    try:
                        busy = deliver_one(db,sender)
                    except Exception:
                        busy = False
                    if not busy:
                        stop.wait(3)
            thread = threading.Thread(target=work,daemon=True,name="trackfit-push")
            thread.start()
        try:
            yield
        finally:
            stop.set()
            if enabled:
                thread.join(timeout=2)
    return lifespan
