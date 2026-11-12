# Auditoria e plano de consolidação do backend (12/11/2026)

## Escopo verificado
- `identity.py`: autenticação local, tokens e vínculo professor/aluno.
- `auth_routes.py`: login e consulta do usuário.
- `workout_routes.py`: criação, leitura, revisão versionada e fila de revisão.
- `ai_routes.py` e `ai_generator.py`: geração demonstrativa e validação da saída.
- `catalog_routes.py`: catálogo público e estrutura de vídeos.
- Histórico de CI: 49 testes aprovados no PR #11; primeira execução do PR #12 com 49/50 aprovados por expectativa desatualizada de filtro. Teste corrigido; aguardar nova execução.

## Correção realizada
O gerador e a API de catálogo tinham listas independentes. Agora o gerador obtém os nomes do catálogo público por meio de um mapeamento explícito de IDs legados; IDs ausentes causam erro na inicialização. Teste verifica o mapeamento. Adicionados `lat_pulldown` e `leg_extension` ao catálogo.

## Sequência de integração recomendada
1. Confirmar CI verde no PR #12 e revisar o diff.
2. Integrar PR #8 (base do backend) na `main` após revisar proteções e testes.
3. Rebase/atualizar a base do PR #10 para `main`, executar CI e integrar.
4. Rebase/atualizar a base do PR #11 para `main`, executar CI e integrar.
5. Rebase/atualizar a base do PR #12 para `main`, executar CI e integrar.
6. Executar testes da `main` e conferir `/health`, `/capabilities`, autenticação e rotas em ambiente local isolado.
Não fazer deploy nem migrar dados reais neste ciclo.

## Riscos pendentes para produção
- Autenticação sem rate limiting, revogação de sessão, recuperação de senha ou fluxo público de cadastro.
- SQLite e criação de tabelas em `identity_db()` por requisição: substituir por migrações e gestão de conexões apropriadas.
- Ausência de controle de orçamento, cotas e idempotência na chamada paga de IA.
- Questionário de saúde demonstrativo não equivale a avaliação clínica.
- Fichas podem ser geradas com nomes livres em endpoints manuais; integrar validação por IDs estáveis antes do aplicativo.
- Ausência de testes de carga, monitoramento, backups, LGPD e infraestrutura de produção.
- Vídeos ainda não curados; player oficial e regras do YouTube obrigatórios.

## Critério de aceite da consolidação
CI verde na `main`, todos os PRs de dependência integrados em ordem, teste de acesso entre alunos e professores, catálogo consistente com a IA, e nenhuma configuração de produção ativada.
