# Aula prática 01 — Uma fila de revisão com Python, SQL e FastAPI

## O que foi entregue
- `POST /v1/ai/student-demo-workout`: aluno autenticado recebe ficha demonstrativa imediatamente.
- `GET /v1/workouts/pending-review`: professor vê até 100 fichas de IA dos próprios alunos ainda não revisadas.
- `POST /v1/workouts/{workout_id}/revisions`: professor edita a ficha, criando nova versão; a ficha sai da fila.

## Estude o código
1. Abra `trackfit_api/workout_routes.py` e encontre `pending_review`.
2. Observe `Depends(require_trainer)`: a API verifica o papel do usuário antes de executar a função.
3. No SQL, `JOIN trainer_students` limita os resultados aos alunos vinculados; `NOT EXISTS` remove fichas que já receberam revisão.
4. Abra `tests/test_student_demo.py`: o teste cria uma ficha com IA simulada, confirma que aparece na fila e depois some após revisão.

## Exercício seu (15 minutos)
No seu computador, crie uma branch de estudo e modifique a consulta para retornar no máximo **20** fichas em vez de 100. Execute `python -m unittest discover -s tests -v`. Depois explique por que a consulta precisa filtrar por `trainer_id`.

## Pontos pendentes antes de clientes reais
Sem notificações push, cadastro público seguro, limites de chamadas pagas, revisão clínica validada, Android ou deploy. A fila é uma consulta calculada, não um sistema de notificações. O protótipo não deve receber dados pessoais reais.
