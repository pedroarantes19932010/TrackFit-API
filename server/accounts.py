"""Compatibilidade entre códigos do Android e a identidade da API v1."""
from datetime import datetime, timezone
from trackfit_api.identity import ensure_identity_tables


def add_code_account(db, user_id, name, role, trainer, token_hash, expires):
    # Contas acessadas por código não têm senha utilizável.
    db.execute("INSERT INTO users VALUES(?,?,?,?)", (user_id, user_id, role, "!"))
    db.execute("INSERT INTO mobile_names VALUES(?,?)", (user_id, name))
    expiry = datetime.fromtimestamp(expires, timezone.utc).isoformat()
    db.execute("INSERT INTO sessions VALUES(?,?,?)", (token_hash, user_id, expiry))
    if role == "student":
        db.execute("INSERT INTO trainer_students VALUES(?,?)", (trainer, user_id))


def columns(db, table):
    return {r[1] for r in db.execute(f"PRAGMA table_info({table})")}


def prepare_accounts(db):
    """O chamador mantém uma transação única, inclusive durante as renomeações."""
    legacy = columns(db, "users") == {"id", "name", "role", "trainer", "token_hash", "expires"}
    if legacy:
        if columns(db, "trainer_students") or "snapshot" not in columns(db, "sessions"):
            raise ValueError("Banco possui esquemas misturados. Revise uma cópia antes de integrar.")
        db.execute("ALTER TABLE users RENAME TO legacy_mobile_users")
        db.execute("ALTER TABLE sessions RENAME TO training_sessions")
    ensure_identity_tables(db)
    db.execute("""CREATE TABLE IF NOT EXISTS mobile_names (
        user_id TEXT PRIMARY KEY REFERENCES users(user_id), name TEXT NOT NULL)""")
    if legacy:
        rows = db.execute("""SELECT id,name,role,trainer,token_hash,expires FROM legacy_mobile_users
                             ORDER BY CASE role WHEN 'trainer' THEN 0 ELSE 1 END""")
        for row in rows:
            add_code_account(db, *row)
        db.execute("DROP TABLE legacy_mobile_users")
