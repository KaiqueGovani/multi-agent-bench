# POC API

## Reviewed WhatsApp Web import

`POST /integrations/whatsapp/import` accepts a reviewed capture from the local
Chrome extension, using the same `X-API-Key` as the other protected routes:

```json
{
  "source": "whatsapp_web",
  "captureId": "9ba8cbb3-d29f-4726-86c6-32c176708f9c",
  "chatTitle": "Conversation for demonstration",
  "targetSourceId": "message-2",
  "messages": [
    {"sourceId": "message-1", "role": "attendant", "text": "Como podemos ajudar?"},
    {"sourceId": "message-2", "role": "customer", "text": "Qual é o horário?"}
  ],
  "architectureMode": "centralized_orchestration",
  "runtimeMode": "real"
}
```

The server persists only the prefix through the selected customer message, in
capture order. Historical messages do not trigger execution. The selected target
creates one run per requested architecture (`all_architectures` creates three).
Successful responses include `conversationId`, `messageId`, `runId`, `runIds`,
`importedMessageCount` and `reused`. Reusing the same capture UUID and prefix is
idempotent across API restarts; changing its content or architecture requires a new
UUID and otherwise returns HTTP 409. Persistence is atomic and needs no migration.

Captures allow at most 200 text messages, 8000 characters per message and 64000
characters overall. Optional `timestamp` values must contain a timezone. The
source identifier and customer/attendant role are retained in message metadata.
Media contents are not extracted by this endpoint. The runtime receives imported
attendant history in every architecture, with a 200-message bound and a snapshot
ending at the current target, so future or sibling responses cannot leak into it.

Real mode checks runtime readiness and selects `architectural-comparison-v4.4`
with the application source adapters. An unavailable live runtime returns HTTP 503.
Mock mode is explicitly selectable for local development. Captures and runs are
application demo data, separate from the frozen research results. This integration
does not send messages to WhatsApp contacts; generated text remains a draft for
the attendant. Chrome extension origins are allowed by CORS only when an API key
is configured, and all such requests still require that key. The Bedrock key
belongs solely in the agent runtime environment, never in extension settings.

Local tests: `uv run pytest tests/test_whatsapp_import.py -q` from `apps/api`.

FastAPI backend for the pharmacy multi-agent POC.

## Scope

This package starts the backend base required by execution plan step 2:

- application factory and `GET /health`
- route modules for conversations, messages, events, and attachments
- Pydantic schemas aligned with `packages/contracts`
- initial in-memory application service for conversation creation and lookup

Persistence, file storage, SSE implementation, and the mock runtime are implemented in later steps.

## Local run

Create a local environment and install dependencies from the repository root:

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -e ./apps/api
```

Start PostgreSQL:

```bash
docker compose -f infra/docker/docker-compose.yml up -d postgres
```

Run migrations from `apps/api`:

```bash
cd apps/api
alembic upgrade head
```

Start the API:

```bash
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

## API key

By default, local development does not require an API key. To protect the API,
set `API_KEY` in `apps/api/.env`:

```bash
API_KEY=replace-with-a-local-development-key
```

When `API_KEY` is set, protected endpoints require `X-API-Key`. The frontend can
send this in development through `apps/web/.env.local`:

```bash
NEXT_PUBLIC_API_KEY=replace-with-a-local-development-key
```

The value must match exactly. `make sync-env` generates a cryptographically
random local key and writes the same value to both files. Existing custom keys
are preserved; the former demonstration key is replaced. `make dev`, `make api`,
and `make web` synchronize the key without replacing the rest of the local
configuration. An explicit `API_KEY` environment or Make override is honored.

Use the small copy-key icon in the main chat header, then paste that value into
the extension's local connection settings. This is the MAB API key; provider
credentials such as Bedrock and Anthropic keys stay separate.

If the web app starts on a port other than `3000`, include that origin in
`CORS_ALLOWED_ORIGINS` and restart the API. The default example allows both
`3000` and `3001`.

If conversation history or message sending returns HTTP 500 after pulling new
commits, run pending migrations before restarting the API:

```bash
cd apps/api
alembic upgrade head
```

## Updating the LLM provider, model, and key while running

Use the LLM settings control in the chat UI to switch between Amazon Bedrock
and the direct Anthropic API, select a model, or replace an expired key without
restarting. Protected `GET /settings/llm` reads the runtime's selected provider,
models, and credential-presence flags. `PUT /settings/llm` accepts
`{"provider":"anthropic","modelId":"claude-haiku-4-5","apiKey":"..."}` and forwards
it to `AI_RUNTIME_URL`. The provider is `bedrock` or `anthropic`; omit `apiKey` or
leave it blank to reuse that provider's key. Switching to a provider without a
configured key is rejected by the runtime. `PUT /settings/bedrock` remains
available for existing clients that only rotate the Bedrock key.

Protected `POST /settings/llm/models` accepts
`{"provider":"anthropic","apiKey":"..."}` and returns
`{"provider":"anthropic","models":[{"id":"...","name":"..."}],"source":"provider"}`.
Omit or leave the key blank to use the credential already held by that provider.
Listing models does not change the active settings or perform inference.
`source: "provider"` identifies a provider response; `source: "catalog"` identifies
the Bedrock fallback catalog when discovery is unavailable and does not confirm
that the key can access those models.

Provider keys are never returned, logged, or saved to the database, browser
storage, or `.env` files. New runs use the selection immediately, while runs
already accepted keep their original provider, model, and key. The selected
provider and model are recorded in each run's experiment metadata from the
runtime's acceptance snapshot, across all input channels. Settings last until
the runtime restarts; its environment supplies the startup configuration again
after a restart.

For a runtime on a different host, configure the same `AI_SERVICE_SECRET` on the
API and runtime. Without that secret, the runtime permits key updates only from
loopback requests without an `Origin` header, such as the local API proxy. A
configured key does not verify its validity with its provider; the next live
request confirms whether it is accepted.

## Conversation names and deletion

The first run names its conversation using the selected model. Naming happens
in parallel with dispatch and is excluded from run latency and token metrics.
Only one title is generated per conversation, including multi-architecture
turns. If naming is unavailable, a short message-based title is kept instead.
Existing untitled conversations are named on their next dispatch, using their
first run's message as the seed; simply opening a conversation makes no model call.
The title is returned in conversation details/lists and published through the
`conversation.updated` event.

`DELETE /conversations/{id}` permanently removes the conversation, messages,
runs, execution events/projections, processing events, reviews, and attachment
objects. Late callbacks return 404. Deleting a conversation does not cancel a
provider request already in progress, but its result cannot recreate the data.
Storage failures keep database references so cleanup can be retried.

## Storage

The default attachment storage provider is `local`. To use MinIO locally, start
the storage service and set the S3-compatible variables from `infra/storage/README.md`.
For production, use the same adapter with `STORAGE_PROVIDER=s3` and cloud bucket
credentials.

Useful endpoints in this phase:

- `POST /conversations`
- `GET /conversations/{conversation_id}`
- `GET /conversations/{conversation_id}/messages`
- `POST /messages`
- `GET /conversations/{conversation_id}/events`
- `GET /conversations/{conversation_id}/events/stream`

The SSE endpoint streams new events for active subscribers. Persisted events remain available through the standard conversation detail and events endpoints.

After `POST /messages`, the API accepts the inbound message and starts a mocked background runtime. The runtime emits processing and actor events, then persists a simulated outbound response. It does not call LLMs or execute real pharmacy logic.

When `RUNTIME_MODE=real` and `AI_RUNTIME_URL` is configured, the API dispatches
an execution-ready payload to the separate agent runtime service. Rich run
events are accepted through `POST /integrations/ai/run-events` and exposed via:

- `GET /runs/{run_id}`
- `GET /runs/{run_id}/execution`
- `GET /runs/{run_id}/execution/stream`
- `GET /runs/{run_id}/comparison-context`

Send a text-only message:

```bash
curl -X POST http://localhost:8000/messages \
  -F "conversationId=<conversation-id>" \
  -F "text=Ola, voces tem dipirona em gotas?" \
  -F 'metadata_json={"timezone":"America/Sao_Paulo","locale":"pt-BR","channel":"web_chat"}'
```

Send a message with an image:

```bash
curl -X POST http://localhost:8000/messages \
  -F "conversationId=<conversation-id>" \
  -F "text=Pode me ajudar a identificar esse produto?" \
  -F 'metadata_json={"timezone":"America/Sao_Paulo","locale":"pt-BR","channel":"web_chat","fileCount":1}' \
  -F "files=@/path/to/image.png;type=image/png"
```
