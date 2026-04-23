# POC contracts

This package contains the initial shared contracts for the pharmacy multi-agent POC.

The goal is to keep backend, frontend, event streaming, persistence, and future channel adapters aligned before implementation starts.

## Files

- `src/enums.ts`: canonical enum values used by API, UI, runtime, events, and persistence.
- `src/domain.ts`: shared domain models and normalized channel messages.
- `src/api.ts`: API request/response contracts and SSE payload shape.
- `schemas/domain.schema.json`: language-neutral JSON Schema for core entities.
- `PAYLOADS.md`: short reference for the first HTTP, multipart, SSE, and adapter payloads.
- `examples/*.json`: representative payloads for the main POC flows.

## Contract rules

- IDs are UUID strings.
- Timestamps are ISO 8601 strings in UTC.
- Field names exposed through HTTP/SSE use camelCase.
- Persistence can map these fields to snake_case internally.
- `metadata` stores operational metadata and must not be blindly forwarded to model prompts.
- `modelContext` stores information that may become useful to an LLM later.
- Every message-processing flow must carry a `correlationId`.
- Every model/agent execution should create a `runId`; `correlationId` is for
  request correlation, while `runId` is the analytical unit for comparison.
- Events must be persisted and associated with a conversation; message-specific events should also include `messageId`.
- Experimental comparisons require stable values for `architectureFamily`,
  `architectureKey`, `architectureVersion`, `routingStrategy`,
  `memoryStrategy`, `toolExecutorMode`, `reviewPolicyVersion`,
  `modelProvider`, `modelName`, `promptBundleVersion`, `toolsetVersion`,
  `experimentId`, and `scenarioId`.

## Initial POC assumptions

- Initial channel is `web_chat`.
- Runtime mode is `mock`.
- Default architecture mode is `centralized_orchestration` until comparative modes are implemented.
- Supported attachment MIME types for the POC are `image/jpeg`, `image/png`, `image/webp`, and `application/pdf`.
- Suggested maximum file size is 5 MB per attachment.
- Suggested maximum file count is 4 attachments per message.
