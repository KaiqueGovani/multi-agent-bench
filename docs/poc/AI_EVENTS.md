# Eventos externos do servico de IA

O endpoint `POST /integrations/ai/events` permite que um servico externo publique
eventos no mesmo historico usado pelo runtime mockado.

Quando `API_KEY` estiver definida, envie `X-API-Key`. Quando
`AI_SERVICE_SECRET` estiver definido, envie tambem `X-AI-Service-Secret`.

Exemplo:

```json
{
  "conversationId": "00000000-0000-0000-0000-000000000000",
  "messageId": "00000000-0000-0000-0000-000000000000",
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

`externalEventId` e usado para idempotencia. Se o mesmo valor for reenviado para
a mesma conversa, a API retorna o evento persistido anteriormente.
