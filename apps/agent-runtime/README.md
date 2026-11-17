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

## Conversation titles

The API calls authenticated `POST /conversations/title` with a first-message
`text` to create a short Portuguese title using the current provider/model.
Naming is separate from instrumented agent execution and has an eight-second
deadline. It returns a short fallback if live inference is disabled or fails.
The API owns the durable once-per-conversation claim and title persistence.

## Updating LLM settings while running

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

`POST /settings/llm/models` accepts `{"provider":"anthropic","apiKey":"..."}`
to load model choices without saving the key or changing the active settings.
An omitted or blank key reuses that provider's configured credential. Anthropic
requires a key and calls its read-only Models API. Bedrock uses a request-scoped
bearer token to list active Anthropic inference profiles in the configured AWS
region, with no mutation of process environment or fallback to IAM credentials.
Both paths limit pagination and use an eight-second request deadline, without
invoking a model.

The response has `provider`, `models` (each with `id` and `name`) and `source`.
`source=provider` identifies a live listing. If Bedrock has no key or discovery
is denied/unavailable, `source=catalog` returns the current configured model and
documented US profile choices for supported source regions. Catalog choices do
not verify account permissions or entitlement; a custom model ID remains valid
input. AWS API keys support Bedrock control-plane actions, but a key's IAM
permissions can still deny listing.

References: [Anthropic Models API](https://platform.claude.com/docs/en/api/python/models/list),
[AWS API key support](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-supported.html),
[ListInferenceProfiles](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_ListInferenceProfiles.html),
[Haiku 4.5 IDs](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html),
and [Sonnet 4.5 IDs](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-4-5.html).

Set the same `AI_SERVICE_SECRET` on the API and runtime to authorize updates
through `X-AI-Service-Secret`. Without that secret, the runtime accepts updates
only from loopback requests without an `Origin` header. Use one HTTP worker for
this in-memory setting; inference remains parallel in isolated subprocesses.
