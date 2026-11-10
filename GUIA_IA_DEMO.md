# Geração de fichas com IA — protótipo controlado

Endpoint: `POST /v1/ai/demo-workout`. Exige sessão de professor vinculado ao aluno fictício. Chama a API da OpenAI uma vez, valida IDs e parâmetros contra catálogo fechado e salva a ficha imediatamente com `source=ai`. A revisão posterior do professor usa `POST /v1/workouts/{id}/revisions`.

## Configuração

- Defina `TRACKFIT_DB_PATH` e crie usuários fictícios de teste conforme `GUIA_AUTENTICACAO.md`.
- Configure `OPENAI_API_KEY` **somente no servidor**, nunca no aplicativo ou repositório.
- O modelo padrão é `gpt-4.1-mini`, com até 500 tokens de saída por chamada.
- Rode `python -m unittest discover -s tests -v`; testes do gerador usam respostas simuladas, sem custo de API.

Exemplo de corpo JSON (apenas dados fictícios):

```json
{
  "student_id": "student1",
  "goal": "general_fitness",
  "experience": "beginner",
  "adult": true,
  "cleared_for_exercise": true,
  "has_pain_or_injury": false,
  "has_medical_restriction": false
}
```

## Limites

**Não usar para prescrição real nem expor na internet.** As declarações de saúde são booleanos fornecidos pelo solicitante e não substituem avaliação clínica ou profissional. O catálogo é mínimo e a geração não avalia individualmente intensidade, progressão, contraindicações, histórico, limitações, técnica ou preferências. Não existe ainda notificação ao professor, interface Android, registro de aceite ou validação profissional de segurança. O modelo pode retornar dados inválidos: nesses casos, a API falha sem publicar ficha. Custos e cotas devem ser controlados na conta OpenAI, e o endpoint precisa de rate limiting antes de qualquer teste público.
