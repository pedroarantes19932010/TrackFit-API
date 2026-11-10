# TrackFit — arquitetura incremental do MVP

## Fluxo de produto aprovado

1. Aluno informa objetivos e dados mínimos, após cadastro e consentimento.
2. Serviço gera proposta de ficha, validada por regras técnicas antes de publicar.
3. Ficha aprovada pelas regras é disponibilizada imediatamente ao aluno, sem aguardar o professor.
4. Professor recebe aviso e revisa quando puder.
5. A revisão cria **nova versão**; a anterior é preservada para auditoria.

## O que existe nesta branch

- `Treino_v6.py`: registro **local** de treinos realizados, preservado.
- `trackfit_api/main.py`: endpoints de saúde e capacidades, sem dados pessoais.
- `trackfit_api/workouts.py`: núcleo de domínio para publicação e revisão de fichas em memória, com versões imutáveis e testes.
- **Ainda não há** geração de IA, integração de notificações, autenticação, banco de dados, Android ou endpoints de fichas.

## Próximas entregas em ordem de dependência

1. Persistência transacional (SQLite local para desenvolvimento; PostgreSQL no serviço).
2. Autenticação e autorização por aluno/professor; não confiar em identificadores fornecidos pelo cliente.
3. Endpoints de ficha com controle de versão, concorrência e auditoria.
4. Questionário de triagem e regras de segurança; casos com alertas exigem encaminhamento/revisão antes da publicação.
5. Integração de IA no backend, com validação estruturada, limites de custo e registro da versão do modelo.
6. Notificação ao professor e aplicativo Android.
7. Testes de integração, privacidade/LGPD, implantação e piloto fechado.

**Aviso:** este núcleo é apenas um modelo de regras. Não deve ser usado para prescrever exercícios reais ou armazenar dados sensíveis sem controles de acesso e validação profissional.
