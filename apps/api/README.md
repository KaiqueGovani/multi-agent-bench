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
