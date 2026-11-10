# API de fichas — protótipo local

Esta API expõe operações de fichas versionadas **somente para desenvolvimento**. Usa uma única chave compartilhada, que não identifica aluno nem professor. **Não use em produção ou com dados pessoais reais.**

## Executar localmente

```bash
python -m pip install -r requirements-api.txt
export TRACKFIT_DEV_API_KEY="gere-um-segredo-aleatorio-de-pelo-menos-32-caracteres"
export TRACKFIT_DB_PATH="./trackfit_dev.sqlite"
python -m uvicorn trackfit_api.main:app --host 127.0.0.1 --port 8000
```

No PowerShell, use `$env:TRACKFIT_DEV_API_KEY="..."` e `$env:TRACKFIT_DB_PATH="..."` em vez de `export`. Gere uma chave aleatória real com `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

Em `http://127.0.0.1:8000/docs`, os endpoints exigem o cabeçalho `x-trackfit-key`.

- `POST /v1/workouts`: cria ficha manual, publicada imediatamente.
- `GET /v1/workouts/{id}`: lê versão publicada.
- `GET /v1/workouts/{id}/versions`: lê histórico.
- `POST /v1/workouts/{id}/revisions`: cria nova versão, exige `expected_version` atual.

## Limitações críticas

- A chave é compartilhada e permite acesso a **todas** as fichas: não há separação de contas ou autorização por usuário.
- `student_id` e `reviewer_id` são campos fornecidos pelo cliente e não comprovam identidade.
- Não há IA, triagem de saúde, auditoria de identidade, criptografia, consentimento, controle de acesso individual, rate limiting nem notificações.
- Não exponha a API à internet nem inclua a chave em aplicativo Android distribuído.
- Próxima etapa obrigatória antes de usuários reais: autenticação individual, papéis, vínculo professor-aluno, autorização por recurso e testes.
