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
- `AWS_BEARER_TOKEN_BEDROCK` when `ENABLE_LIVE_LLM=true`

The default local model target is:

```txt
us.anthropic.claude-haiku-4-5-20251001-v1:0
```
