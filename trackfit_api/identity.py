"""Identidade local: senhas scrypt, tokens aleatórios e vínculo professor-aluno."""
import hashlib
from contextvars import ContextVar
import hmac
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, Header, HTTPException

from trackfit_api.storage import connect

SESSION_HOURS = 12
request_database = ContextVar("trackfit_request_database", default=None)


def identity_db():
    import os
    path = request_database.get() or os.environ.get("TRACKFIT_DB_PATH")
    if not path:
        raise HTTPException(status_code=503, detail="Banco não configurado")
    db = connect(Path(path))
    ensure_identity_tables(db)
    db.commit()
    return db


def ensure_identity_tables(db):
    db.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL CHECK(role IN ('trainer','student')),
        password_hash TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS trainer_students (
        trainer_id TEXT NOT NULL, student_id TEXT NOT NULL,
        PRIMARY KEY (trainer_id, student_id),
        FOREIGN KEY(trainer_id) REFERENCES users(user_id),
        FOREIGN KEY(student_id) REFERENCES users(user_id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS sessions (
        token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL,
        expires_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(user_id))""")


def hash_password(password: str) -> str:
    if not 12 <= len(password) <= 256:
        raise ValueError("Senha deve ter entre 12 e 256 caracteres")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + ":" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":")
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
        return hmac.compare_digest(digest, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False


def authenticate(username: str, password: str) -> str | None:
    with identity_db() as db:
        row = db.execute("SELECT user_id,password_hash FROM users WHERE username=?", (username,)).fetchone()
        if not row or not verify_password(password, row[1]):
            return None
        token = secrets.token_urlsafe(32)
        expiry = (datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)).isoformat()
        db.execute("INSERT INTO sessions VALUES (?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), row[0], expiry))
    return token


def current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token necessário")
    token = authorization.removeprefix("Bearer ")
    if not token or len(token) > 256:
        raise HTTPException(status_code=401, detail="Token inválido")
    with identity_db() as db:
        row = db.execute(
            """SELECT u.user_id,u.role,s.expires_at FROM sessions s
               JOIN users u ON u.user_id=s.user_id WHERE s.token_hash=?""",
            (hashlib.sha256(token.encode()).hexdigest(),),
        ).fetchone()
    if not row or datetime.fromisoformat(row[2]) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    return {"user_id": row[0], "role": row[1]}


def require_trainer(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "trainer":
        raise HTTPException(status_code=403, detail="Somente professor")
    return user


def can_access(db: sqlite3.Connection, user: dict, student_id: str) -> bool:
    if user["role"] == "student":
        return user["user_id"] == student_id
    return db.execute(
        "SELECT 1 FROM trainer_students WHERE trainer_id=? AND student_id=?",
        (user["user_id"], student_id),
    ).fetchone() is not None


def require_access(db: sqlite3.Connection, user: dict, student_id: str) -> None:
    if not can_access(db, user, student_id):
        raise HTTPException(status_code=403, detail="Sem acesso à ficha")
