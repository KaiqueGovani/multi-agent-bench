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

After installing dependencies:

```bash
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/health
```
