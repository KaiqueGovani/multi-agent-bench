# Eventos externos do servico de IA

O endpoint `POST /integrations/ai/events` permite que um servico externo publique
eventos no mesmo historico usado pelo runtime mockado.

O chat-api despacha runs para o servico de IA propagando `traceparent` e um
`baggage` minimo com `conversation_id`, `message_id`, `run_id`,
`architecture_key`, `model_key` e `experiment_id`. Esses valores devem ser
usados pelo servico de IA/Strands como atributos de spans, logs e metricas.

Quando `API_KEY` estiver definida, envie `X-API-Key`. Quando
`AI_SERVICE_SECRET` estiver definido, envie tambem `X-AI-Service-Secret`.

Exemplo:

```json
{
  "conversationId": "00000000-0000-0000-0000-000000000000",
  "messageId": "00000000-0000-0000-0000-000000000000",
  "runId": "00000000-0000-0000-0000-000000000000",
  "eventType": "actor.progress",
  "actorName": "external_ai_service",
  "correlationId": "00000000-0000-0000-0000-000000000000",
  "status": "running",
  "externalEventId": "provider-event-123",
  "source": "ai_service",
  "payload": {
    "step": "tool_call",
    "message": "Processing external AI event",
    "progressPercent": 40
  }
}
```

`runId` e usado para vincular o evento externo a uma execucao especifica. Quando
informado, o chat-api valida se a run pertence a `conversationId` e `messageId`.

`externalEventId` e usado para idempotencia junto da run. Se o mesmo valor for
reenviado para a mesma conversa e run, a API retorna o evento persistido
anteriormente.

## Conclusao de run

O servico de IA deve concluir a execucao chamando `PATCH /runs/{run_id}` com o
mesmo `X-API-Key` e `X-AI-Service-Secret`. Esse payload consolida somente o
resumo transacional necessario para comparacao futura; spans, logs e metricas
detalhadas permanecem no backend OpenTelemetry.

Exemplo:

```json
{
  "status": "completed",
  "externalRunId": "strands-run-001",
  "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
  "totalDurationMs": 4012,
  "humanReviewRequired": false,
  "finalOutcome": "answered",
  "summary": {
    "timeToFirstPublicEventMs": 180,
    "timeToFirstPartialResponseMs": 712,
    "inputTokens": 3210,
    "outputTokens": 410,
    "totalTokens": 3620,
    "toolCallCount": 4,
    "toolErrorCount": 0,
    "loopCount": 3,
    "stopReason": "completed"
  }
}
```

Ao receber a conclusao, o chat-api atualiza a `run` e emite um evento publico na
timeline: `processing.completed`, `review.required` ou `actor.failed`,
dependendo do status final.
