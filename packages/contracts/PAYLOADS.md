# POC payloads

This document summarizes the first API and event payloads. JSON examples live in `examples/`.

## POST /conversations

Creates a conversation for a channel.

Request example: `examples/create-conversation-request.json`

Response example: `examples/create-conversation-response.json`

Required response fields:

- `conversationId`
- `status`
- `channel`
- `createdAt`

## POST /messages

Receives text, one or more images, and client metadata.

Transport: `multipart/form-data`

Multipart fields:

- `conversationId`: optional UUID. If omitted, backend may create a conversation.
- `text`: optional text. A message must contain text, at least one file, or both.
- `files[]`: zero or more image files.
- `metadata_json`: JSON string matching the shape shown in `examples/send-message-text-metadata.json`.
- `clientMessageId`: optional temporary client-side ID.

Response example: `examples/send-message-response.json`

Required response fields:

- `messageId`
- `conversationId`
- `status`
- `correlationId`
- `acceptedAt`

## GET /conversations/{conversation_id}/events/stream

Streams processing events through Server-Sent Events.

SSE frame shape:

```txt
event: processing.event
id: <eventId>
data: <SseProcessingEvent JSON>
```

SSE data example: `examples/sse-event-actor-invoked.json`

Final response event example: `examples/response-final-event.json`

## Normalized channel message

Adapters must transform channel-specific input into `NormalizedInboundMessage`.

Example: `examples/normalized-inbound-message.json`

The application layer should process normalized messages instead of web-specific or WhatsApp-specific payloads.

## Human review

When the runtime requires supervision, it emits `review.required` and creates a `ReviewTask`.

Review task example: `examples/review-task.json`

## Mock processing sequence

The initial runtime should emit this sequence for a standard successful flow:

1. `message.received`
2. `attachment.validation.started`
3. `attachment.validation.completed`
4. `processing.started`
5. `actor.invoked`
6. `actor.completed`
7. `response.final`
8. `processing.completed`

