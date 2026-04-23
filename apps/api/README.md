# POC API

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

The value must match exactly. For the local POC setup used in this repository,
both files can use:

```bash
API_KEY=poc-dev-key-2026
NEXT_PUBLIC_API_KEY=poc-dev-key-2026
```

If the web app starts on a port other than `3000`, include that origin in
`CORS_ALLOWED_ORIGINS` and restart the API. The default example allows both
`3000` and `3001`.

If conversation history or message sending returns HTTP 500 after pulling new
commits, run pending migrations before restarting the API:

```bash
cd apps/api
alembic upgrade head
```

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
