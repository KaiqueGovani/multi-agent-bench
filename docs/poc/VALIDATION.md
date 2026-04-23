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
- stream SSE em tempo real
- persistencia de eventos
- resposta final mockada
- refresh/historico via `GET /conversations/{id}`
- criacao de tarefa de revisao humana simulada

## Fixtures

Os cenarios ficam em `packages/test-fixtures/scenarios`:

- `faq-question`
- `stock-availability`
- `product-image`
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
```
