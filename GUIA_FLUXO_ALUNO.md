# Fluxo de demonstração: aluno primeiro

Endpoint `POST /v1/ai/student-demo-workout`, com token Bearer do próprio aluno e mesmo corpo do exemplo em `GUIA_IA_DEMO.md`.

O backend confirma identidade do aluno, vínculo com professor e critérios demonstrativos de elegibilidade **antes** de consumir API paga. A ficha é publicada com versão 1 sem aprovação prévia; o professor vinculado pode consultar e revisar para versão 2 usando os endpoints existentes.

Os testes de ponta a ponta simulam a resposta da IA e verificam bloqueio de aluno não vinculado, tentativa de gerar ficha para outra pessoa e declaração de lesão. Rodar `python -m unittest discover -s tests -v`.

**Limitações críticas:** este fluxo não tem notificações push, Android, controle de orçamento por aluno, rate limiting, triagem clínica validada ou verificação humana da adequação dos exercícios. Não usar com alunos reais ou publicar na internet. Não armazenar dados de saúde reais nesse protótipo.
