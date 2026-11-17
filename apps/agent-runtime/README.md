# Agent Runtime

Separate Strands-based runtime service for `multi-agent-bench`.

## Local run

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -e ./apps/agent-runtime
uvicorn app.main:app --reload --app-dir apps/agent-runtime
```

## Required environment

- `BEDROCK_MODEL_ID`
- `MODEL_PROVIDER=bedrock` (default) or `MODEL_PROVIDER=anthropic`
- `AWS_BEARER_TOKEN_BEDROCK` for live Bedrock inference
- `ANTHROPIC_API_KEY` and optionally `ANTHROPIC_MODEL_ID` for direct Claude inference

The default local model target is:

```txt
us.anthropic.claude-haiku-4-5-20251001-v1:0
```

## Updating the Bedrock key while running

The app reads `GET /settings/llm` and updates `PUT /settings/llm` with a JSON body
such as `{"provider":"anthropic","modelId":"claude-haiku-4-5-20251001","apiKey":"..."}`.
Each provider retains its own model and key in memory; omit or leave `apiKey`
blank to reuse that provider's configured credential. The response contains only
status, model IDs and credential-presence flags. The next accepted run uses the
selected provider and model across all supported architectures and comparison
protocols; already accepted runs retain their original provider, model and key.
Restarting the runtime restores the environment configuration. Saving does not
check key validity with either provider; the next inference call does.

`PUT /settings/bedrock` remains available with an `apiKey` JSON field. It updates
the Bedrock credential without changing the active provider.

Set the same `AI_SERVICE_SECRET` on the API and runtime to authorize updates
through `X-AI-Service-Secret`. Without that secret, the runtime accepts updates
only from loopback requests without an `Origin` header. Use one HTTP worker for
this in-memory setting; inference remains parallel in isolated subprocesses.
