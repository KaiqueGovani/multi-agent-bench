# Validacao ponta a ponta da POC

Esta validacao confirma que a POC executa o fluxo tecnico principal sem operacoes manuais fora da API e da UI.

## Comando principal

```powershell
python scripts/run_e2e_validation.py
```

Por padrao, o script usa `http://127.0.0.1:8000`. Para outro endereco:

```powershell
python scripts/run_e2e_validation.py --api-base http://127.0.0.1:8000
```

Se a API estiver protegida por `API_KEY`, exporte a mesma chave antes de rodar
os scripts:

```powershell
$env:POC_API_KEY="sua-chave-local"
python scripts/run_e2e_validation.py
```

## Cobertura automatizada

- `GET /health`
- criacao de conversa
- envio de mensagem de texto
- envio de imagem valida
- rejeicao de anexo invalido
- envio de PDF valido
- stream SSE em tempo real
- replay de stream SSE por ultimo evento conhecido
- persistencia de eventos
- resposta final mockada
- refresh/historico via `GET /conversations/{id}`
- criacao de tarefa de revisao humana simulada
- captura de dimensoes de imagem
- ingestao idempotente de evento externo do servico de IA

## Fixtures

Os cenarios ficam em `packages/test-fixtures/scenarios`:

- `faq-question`
- `stock-availability`
- `product-image`
- `document-pdf`
- `human-review-needed`
- `invalid-attachment`

Para rodar apenas as fixtures:

```powershell
python scripts/run_fixture_scenarios.py --timeout 12
```

## Criterio de sucesso

A etapa e considerada valida quando o comando principal retorna:

```text
PASS health
PASS fixtures
PASS sse-stream
PASS sse-replay
PASS external-ai-event
```

## Validacao de storage MinIO

O script principal valida o fluxo da API usando o provider configurado. Para
validar MinIO, suba a stack de storage e execute a API com:

```powershell
$env:STORAGE_PROVIDER="minio"
$env:STORAGE_BUCKET="multi-agent-bench-poc"
$env:STORAGE_ENDPOINT_URL="http://127.0.0.1:9000"
$env:STORAGE_ACCESS_KEY="minioadmin"
$env:STORAGE_SECRET_KEY="minioadmin"
python scripts/run_e2e_validation.py
```

Se `AI_SERVICE_SECRET` estiver definido na API, exporte tambem:

```powershell
$env:POC_AI_SERVICE_SECRET="sua-chave-local"
```
