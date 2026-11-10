# TrackFit — API inicial (etapa 1)

Esta branch parte de `codex/registro-treinos-seguro` e preserva `Treino_v6.py` e seus testes. Não há migração automática nem exposição do histórico local.

## Instalação e execução

Python 3.10+:

```bash
python -m pip install -r requirements-api.txt
python -m uvicorn trackfit_api.main:app --reload --host 127.0.0.1 --port 8000
```

No navegador local, abra `http://127.0.0.1:8000/docs`. Endpoints: `GET /health` e `GET /capabilities`.

Testes: `python -m unittest discover -s tests -v` (após instalar as dependências). Os testes legados permanecem.

## Limites importantes

Esta etapa **não** implementa cadastro, login, armazenamento de dados de clientes, IA, prescrição de exercícios ou Android. Não exponha o servidor publicamente: ainda faltam autenticação, autorização, proteção de dados, banco transacional, logs e política de privacidade. Não suba históricos com dados reais ao GitHub.

## Próximas etapas

1. Autenticação e papéis de aluno/professor, com autorização por recurso e testes.
2. Banco de dados e cadastro mínimo de alunos com consentimento e controles LGPD.
3. Modelo de fichas versionadas e fluxo de publicação imediata com revisão posterior do professor.
4. Geração assistida por IA com validação, restrições de segurança, rastreabilidade e revisão profissional.
5. Interface mobile Android e notificações ao professor.

Nenhuma ficha é gerada automaticamente nesta versão.
