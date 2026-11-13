"""Administração local do código de acesso do treinador do piloto."""
import argparse
import secrets
import time
from datetime import datetime, timezone

from server.accounts import add_code_account
from server.app import create_app, uid, digest


def trainer_code(app, name, renew=False):
    token = secrets.token_urlsafe(32)
    expires = time.time() + 30 * 86400
    with app.state.db(True) as db:
        if renew:
            trainers = db.execute("""
                SELECT u.user_id FROM users u JOIN mobile_names n USING(user_id)
                WHERE u.role='trainer' AND u.password_hash='!'
            """).fetchall()
            if len(trainers) != 1:
                raise ValueError("A renovação exige exatamente um treinador do piloto com acesso por código.")
            trainer_id = trainers[0][0]
            # Só as credenciais e os destinos de push da conta são substituídos.
            db.execute("DELETE FROM sessions WHERE user_id=?", (trainer_id,))
            db.execute("""DELETE FROM push_jobs WHERE binding IN
                       (SELECT binding FROM push_devices WHERE trainer=?)""", (trainer_id,))
            db.execute("DELETE FROM push_devices WHERE trainer=?", (trainer_id,))
            db.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)",
                       (digest(token), trainer_id, datetime.fromtimestamp(expires, timezone.utc).isoformat()))
        else:
            if db.execute("SELECT 1 FROM users WHERE role='trainer'").fetchone():
                raise ValueError("Treinador já cadastrado. Para trocar o código do piloto, use --renew.")
            trainer_id = uid()
            add_code_account(db, trainer_id, name, 'trainer', trainer_id, digest(token), expires)
    return token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group()
    options.add_argument('--name', help='Nome do treinador no cadastro inicial.')
    options.add_argument('--renew', action='store_true', help='Revoga os acessos anteriores do treinador do piloto.')
    args = parser.parse_args()
    try:
        token = trainer_code(create_app(), args.name or 'Pedro', args.renew)
    except ValueError as exc:
        parser.exit(1, str(exc)+'\n')
    print('Código privado do treinador (válido por 30 dias; guarde em local seguro):')
    print(token)


if __name__ == '__main__':
    main()
