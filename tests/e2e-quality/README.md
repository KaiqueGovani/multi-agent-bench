# E2E Quality Tests

Scenario-driven end-to-end tests for the Multi-Agent Bench API.
Full spec: [docs/testing/e2e-quality-framework.md](../../docs/testing/e2e-quality-framework.md).

## Quick Start

De dentro do pacote:

```bash
cd tests/e2e-quality
uv sync
uv run pytest -v
# ou: uv run pytest -k dipirona -v
```

Ou, a partir da raiz do repositório:

```bash
make test-quality             # roda tudo
make test-quality-report      # gera HTML em var/reports/quality/report.html
```

Pré-requisito: backend rodando (`make up` ou `docker compose -f infra/docker/docker-compose.yml up -d`).

## Adicionar um cenário

1. Editar `scenarios/pharmacy.yaml` (ou criar outro `.yaml` na mesma pasta).
2. Adicionar um bloco em `cases:` com `id`, `input.text` e `expected.route`.
3. Rodar `uv run pytest -k <id> -v` e ajustar `response_contains_any/none` / `event_types` até passar.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `API_BASE_URL` | `http://127.0.0.1:8000` | Base URL of the running API |
| `API_KEY` | `poc-dev-key-2026` | API key for `X-API-Key` header |

## How It Works

YAML files in `scenarios/` define test cases. Each case specifies input text,
expected route, event types, and response assertions. The `conftest.py` hook
generates the cartesian product of cases × architectures so each combination
runs as a separate pytest parametrized test.

## HTML Report

```bash
uv run pytest -v --html=../../var/reports/quality/report.html
```
