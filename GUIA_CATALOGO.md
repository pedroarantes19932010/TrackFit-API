# Catálogo de exercícios — protótipo

Endpoints públicos demonstrativos:
- `GET /v1/exercises` — lista exercícios; filtros opcionais `muscle_group` e `search`.
- `GET /v1/exercises/{exercise_id}` — detalhes e lista de vídeos.

Seis exercícios iniciais são exemplos editoriais estáticos, **não** uma biblioteca de prescrição clínica. Cada vídeo usa apenas o ID oficial do YouTube (11 caracteres), categoria `demonstration`, `common_mistakes` ou `tips` e nome do criador. O aplicativo deverá usar o player incorporado oficial, respeitar disponibilidade, direitos autorais e termos do YouTube. Nenhum vídeo foi associado ainda: a curadoria deve verificar permissão, qualidade e disponibilidade. Não baixar, copiar ou prometer receita por visualizações de terceiros.

Próximos passos: persistência com edição restrita ao administrador, curadoria, vincular exercícios do gerador ao catálogo, interface Flutter e testes de integração.
