# Autenticação individual — protótipo local

## O que existe

- Login por usuário/senha com derivação `scrypt` e sal aleatório.
- Token de sessão aleatório, armazenado no banco apenas como SHA-256, expira em 12 horas.
- Papéis `trainer` e `student`.
- Acesso à ficha permitido ao aluno titular e ao professor vinculado.
- Criação e revisão de fichas somente por professor vinculado; o autor da revisão é extraído da sessão, nunca de um campo arbitrário.

## Como testar

`python -m pip install -r requirements-api.txt`

`python -m unittest discover -s tests -v`

Para uso local, configure `TRACKFIT_DB_PATH` para um banco de teste. Não existe cadastro público. Crie usuários de teste exclusivamente via script local que use `identity_db()` e `hash_password()` (consulte `tests/test_identity.py`).

## Antes de qualquer publicação

**Não está pronto para produção nem para alunos reais.** Ainda faltam cadastro e provisionamento seguros, recuperação e troca de senha, revogação/logout, rate limiting contra tentativas de login, HTTPS, auditoria, backups, proteção de dados pessoais, validação de professor responsável e políticas LGPD. O banco SQLite local não deve ser exposto na internet. Não colocar token ou segredo fixo em APK. O controle de vínculo é um primeiro isolamento, não uma auditoria de segurança.

O antigo cabeçalho `x-trackfit-key` não autentica mais as rotas de fichas nesta branch; use `Authorization: Bearer <token>`.
