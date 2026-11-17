# POC web

Next.js frontend for the pharmacy multi-agent POC.

## Local run

Install dependencies from `apps/web`:

```bash
npm install
```

Run the frontend:

```bash
npm run dev
```

Default URL:

```txt
http://localhost:3000
```

The frontend expects the API at:

```txt
http://127.0.0.1:8000
```

Override with:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## Changing the provider, model, or API key

The small **Copiar chave da extensão** icon in the main header copies the local
MAB API key so it can be pasted into the extension's connection settings. Local
setup generates a random key shared by the API and web app and retains it across
restarts. The copied value is the MAB connection key, separate from provider keys.

In the chat header, select **Bedrock** (or **Anthropic** when active). Choose
**Amazon Bedrock** or **Anthropic (Claude)**. Each provider retains its own model
and key, so switching back can reuse an existing credential.

Paste a key and select **Carregar modelos** to populate the **Modelo** picker.
Anthropic requires a new or previously configured Anthropic API key. Bedrock
uses available inference profiles when permitted and otherwise offers a labeled
catalog. **Outro modelo…** lets you enter a custom model identifier. Loading the
list does not change the active provider or model and does not run inference.

Select **Aplicar configuração** to apply the provider, model, and optional new
key to subsequent web chat and WhatsApp runs immediately. Accepted runs retain
their original configuration. The key input is masked and cleared after a
successful update or closing the dialog. These settings are kept only in server
memory until the runtime restarts; the browser does not save them. Updating the
settings does not enable live mode if it is disabled.

The API and agent runtime must both be running. Use a single runtime HTTP worker
(the default `make runtime` and `make runtime-llm`); its execution pool still runs
LLM requests in parallel. If `AI_SERVICE_SECRET` is set on the runtime, configure
the same value on the API.

## Published experiment

Run `npm ci` and `npm run dev` from `apps/web`, then open
[the v4.4 comparison](http://localhost:3000/research/comparison-v44).
The page reads the 600 sanitized records and summary tables from
`research-data/results/architectural-comparison-v44` in the repository.
The published comparison runs with only the frontend.

## Current scope

- Create a web chat conversation.
- Send text messages to `POST /messages`.
- Upload images and PDFs.
- Subscribe to SSE events for the active conversation.
- Render persisted messages and operational events.
- Render run-centric execution views backed by rich runtime projections.

## Conversation and dashboard views

The shared **Execução** picker lists every run, grouped by the user message that
started it. Its selection stays the same when switching between **Conversa** and
**Visão Geral**. The overview compares architectures for that message and marks
the selected run; **Mais recente** resumes following new requests.

Flow views use the observed agents and communications: centralized fan-out,
horizontal workflow, and a radial swarm. Returns share their original connection;
dashed workflow links indicate execution order rather than a recorded message.
Use the zoom controls, drag the graph, or select **Ajustar** to fit it again.

Conversation titles are generated once from the initial request. The trash action
in the header or history asks for confirmation before permanently removing the
conversation, messages, runs, events, reviews, and attachments. Failed deletion
can be retried without discarding the current view.

The dashboard separates run counts from latency in seconds. Its tool distribution
counts domain tool invocations once, excluding routing and delegation between
agents. Detailed events remain available through the chat's **Atividade** tab.
