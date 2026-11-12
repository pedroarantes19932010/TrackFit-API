"""Cria o primeiro treinador localmente. Nunca imprime credenciais preexistentes."""
import argparse
import secrets
import time
from server.app import create_app, uid, digest

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='Pedro')
    args = parser.parse_args()
    app = create_app()
    token, user_id = secrets.token_urlsafe(32), uid()
    with app.state.db(True) as db:
        if db.execute("SELECT 1 FROM users WHERE role='trainer'").fetchone():
            raise SystemExit('Treinador já cadastrado. Não recriamos nem exibimos o código existente.')
        db.execute('INSERT INTO users VALUES(?,?,?,?,?,?)', (user_id,args.name,'trainer',user_id,digest(token),time.time()+30*86400))
    print('Código privado do treinador (válido por 30 dias; guarde em local seguro):')
    print(token)

if __name__ == '__main__':
    main()
