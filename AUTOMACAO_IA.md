# TrackFit — desenvolvimento automático diário

## Ativação

O agendamento do GitHub Actions **só funciona quando este workflow estiver na branch padrão `main`**. Fazer merge apenas na branch `feat/mvp-api-inicial` não ativa o cron.

1. Revise o PR da automação e integre-o à `main` somente depois de integrar as dependências do MVP (ou use um PR posterior direcionado à `main`).
2. Em GitHub → Settings → Secrets and variables → Actions → **Repository secrets**, crie `OPENAI_API_KEY` com uma chave de API criada em https://platform.openai.com/api-keys. Nunca salve a chave em arquivo ou commit.
3. Em **Repository variables**, opcionalmente configure `TRACKFIT_AGENT_MODEL` (padrão `gpt-4.1-mini`). Confirme a disponibilidade do modelo na sua conta.
4. Em Settings → Actions → General, habilite execução de Actions e permita que `GITHUB_TOKEN` crie Pull Requests, caso a organização/repositório exija. Permissões do workflow são restritas ao job.
5. Configure na plataforma da OpenAI um orçamento mensal pequeno e alertas de gasto. Exemplo inicial: **US$ 5/mês**, ajustável. Os limites no código (1 chamada, até 4.500 tokens de saída, 2 arquivos, execução de 12 min) limitam uso por execução, mas **não garantem teto financeiro mensal**.
6. Em Actions → Daily AI development (PR only) → Run workflow, teste manualmente. Confira logs, PR e testes antes de depender do agendamento.

## Horário e comportamento

Cron `0 12 * * *`: 12:00 UTC = 09:00 em Brasília enquanto o fuso for UTC-03. O GitHub pode iniciar o job com atraso. Se regras de fuso mudarem, atualize o cron.

- A automação gera no máximo **uma proposta por execução**, restrita aos arquivos `trackfit_api/workouts.py` e `tests/test_workouts.py`.
- Se já existir um PR aberto com título `[TrackFit Bot]`, ela não gera outra proposta.
- Só cria PR **rascunho** após executar testes com sucesso.
- Não faz merge automático nem publica código em produção.
- Não modifica workflows, infraestrutura, segredos ou histórico de clientes.
- A automação não é um agente geral capaz de concluir todo o aplicativo: o escopo de alterações é propositalmente pequeno.

## Segurança e limitações

A geração por IA não é confiável por si só: revise cada diff. O workflow usa código gerado em um runner de CI, então há risco residual de código malicioso ou exfiltração; nunca armazene dados sensíveis de clientes no repositório. Não forneça secrets aos testes. O token de GitHub não é persistido pelo checkout, mas o job de publicação precisa de permissão para enviar branch e PR. Use proteção da branch `main` e exigência de aprovação e testes.

O script não utiliza histórico de clientes nem gera prescrições. Sem `OPENAI_API_KEY`, o workflow falha explicitamente, sem cobrar API.

## Desativar

Em GitHub → Actions → Daily AI development → menu de opções → Disable workflow. Alternativamente, remova o cron por PR e merge.
