# Persistência local das fichas — SQLite

Este módulo adiciona persistência transacional de **fichas versionadas** ao núcleo de domínio do TrackFit. Não cria endpoints públicos, contas ou armazenamento de dados reais de alunos.

## Exemplo de uso local

```python
from trackfit_api.storage import connect, save_initial, get_current
from trackfit_api.workouts import Exercise, publish_initial

db = connect("trackfit_dev.db")
ficha = publish_initial("aluno-ficticio", [Exercise("Remada", 3, 12, 60)])
save_initial(db, ficha)
print(get_current(db, ficha.workout_id))
db.close()
```

Execute os testes: `python -m unittest discover -s tests -v`.

## Garantias e limites

- SQLite usa transações e índice único para impedir duas versões publicadas da mesma ficha.
- Revisões antigas são preservadas; atualização concorrente com versão obsoleta é recusada.
- Ainda **não há** autenticação, autorização, criptografia de dados, consentimento, backups gerenciados, migrações ou API de fichas.
- Não use dados de clientes reais nem exponha o banco em serviço público.
- Para o MVP hospedado, avaliar PostgreSQL com autenticação e controles LGPD.
