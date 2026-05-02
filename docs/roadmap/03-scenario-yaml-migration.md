# 03 — Migração dos Cenários JSON → YAML

> Consolidar os dois conjuntos de cenários de teste (JSON fixtures + YAML e2e-quality) em uma única fonte de verdade YAML, estendendo o schema para cobrir attachments, erros HTTP e métricas de benchmark.

---

## Índice

1. [Contexto](#1-contexto)
2. [Estado Atual](#2-estado-atual)
3. [Estado Desejado](#3-estado-desejado)
4. [Schema YAML Estendido](#4-schema-yaml-estendido)
5. [Exemplo Completo — 2 Suites](#5-exemplo-completo--2-suites)
6. [Implementação Passo a Passo](#6-implementação-passo-a-passo)
7. [Como Validar](#7-como-validar)
8. [Riscos e Mitigações](#8-riscos-e-mitigações)
9. [Critérios de Pronto](#9-critérios-de-pronto)
10. [Fora de Escopo](#10-fora-de-escopo)

---

## 1. Contexto

Hoje existem **dois conjuntos paralelos** de cenários de teste:

| Aspecto | JSON Fixtures (`packages/test-fixtures/`) | YAML e2e-quality (`tests/e2e-quality/`) |
|---|---|---|
| **Formato** | 6 arquivos `.json` | 1 arquivo `pharmacy.yaml` |
| **Cliente HTTP** | `urllib` via `run_fixture_scenarios.py` | `httpx` via `api_client.py` |
| **Asserções** | `httpStatus`, `route`, `actor`, `eventTypes`, `reviewRequired` | `route`, `event_types`, `response_contains_any/none`, `final_actor` |
| **Attachments** | Base64 inline / path relativo | Não suportado ainda |
| **Arquiteturas** | Não parametriza | Produto cartesiano via `defaults.architectures` |
| **Benchmark** | Consumido por `run_architecture_benchmark.py` | Não integrado ainda |

A duplicação causa:
- **Drift silencioso** — um cenário é atualizado num lugar e esquecido no outro.
- **Dois runners** — manter `urllib` + `httpx` em paralelo sem ganho.
- **Asserções incompletas** — o JSON não valida conteúdo da resposta; o YAML não testa attachments nem erros HTTP.

O framework `e2e-quality` é o futuro. Esta melhoria consolida tudo nele.

---

## 2. Estado Atual

### 2.1 JSON Fixtures (6 arquivos)

| ID | Texto (resumo) | Route | Actor | Attachments | HTTP Status | reviewRequired |
|---|---|---|---|---|---|---|
| `faq-question` | "Qual o horário de funcionamento…" | `faq` | `faq_agent` | — | 202 | `false` |
| `stock-availability` | "Tem dipirona em estoque?" | `stock_lookup` | `stock_agent` | — | 202 | `false` |
| `product-image` | "Consegue identificar este produto…" | `image_intake` | `image_intake_agent` | `tiny-product.png` (base64) | 202 | `false` |
| `document-pdf` | "Segue um documento para análise…" | `image_intake` | `image_intake_agent` | `tiny-document.pdf` (base64) | 202 | `false` |
| `human-review-needed` | "Preciso que um supervisor faça revisão…" | `faq` | `faq_agent` | — | 202 | `true` |
| `invalid-attachment` | "Estou anexando um arquivo inválido…" | — | — | `not-an-image.txt` | **400** | — |

### 2.2 YAML Existente (1 caso)

```yaml
# tests/e2e-quality/scenarios/pharmacy.yaml
suite: pharmacy
cases:
  - id: dipirona_dor_de_cabeca
    input:
      text: "Posso tomar dipirona pra dor de cabeça?"
    expected:
      route: faq
      final_actor: supervisor_agent
      actor_reasoning_present: true
      event_types: [processing.started, actor.reasoning, response.final, processing.completed]
      response_contains_any: [farmacêutico, médico, profissional, "[modo mock]"]
      response_contains_none: ["{'", "{ '", "Supervisor central concluiu"]
```

---

## 3. Estado Desejado

**8 cenários** distribuídos em 2 suites YAML, cobrindo todos os 6 fixtures JSON migrados + 2 cenários novos:

| # | ID | Suite | Origem | Descrição |
|---|---|---|---|---|
| 1 | `faq_horario_funcionamento` | `pharmacy` | JSON `faq-question` | FAQ simples — horário de funcionamento |
| 2 | `dipirona_dor_de_cabeca` | `pharmacy` | YAML existente | FAQ clínico — dipirona |
| 3 | `consulta_estoque_dipirona` | `pharmacy` | JSON `stock-availability` | Consulta de estoque |
| 4 | `revisao_humana_forcada` | `pharmacy` | JSON `human-review-needed` | Força `review.required` via metadata |
| 5 | `interacao_medicamentosa` | `pharmacy` | **NOVO** | Interação perigosa → deve forçar review |
| 6 | `multi_turn_swarm` | `pharmacy` | **NOVO** | Múltiplas perguntas para testar swarm |
| 7 | `imagem_produto` | `attachments` | JSON `product-image` | Upload de imagem PNG |
| 8 | `documento_pdf` | `attachments` | JSON `document-pdf` | Upload de PDF |
| 9 | `anexo_invalido` | `attachments` | JSON `invalid-attachment` | Arquivo `.txt` → HTTP 400 |

Todos os cenários rodam com `architectures: [centralized_orchestration, structured_workflow, decentralized_swarm]` por padrão.

---

## 4. Schema YAML Estendido

Campos **novos** marcados com 🆕:

```yaml
suite: string                          # identificador da suite
description: string                    # descrição livre

defaults:
  architectures: list[string]          # produto cartesiano com cada case
  timeout_seconds: int                 # default 60

cases:
  - id: string                         # único dentro da suite
    input:
      text: string                     # mensagem do usuário
      locale: string                   # default "pt-BR"
      attachments:                     # 🆕 lista de arquivos para multipart upload
        - path: string                 #    caminho relativo à raiz do repo
          mime_type: string            #    ex: "image/png", "application/pdf"

    conversation_metadata: dict        # metadata extra na criação da conversa
    message_metadata: dict             # metadata extra no envio da mensagem

    expected:
      route: string                    # rota esperada (faq, stock_lookup, image_intake, etc.)
      http_status: int                 # 🆕 status HTTP esperado (default 202)
      error_contains: string           # 🆕 substring esperada no corpo de erro (para http_status >= 400)
      final_actor: string              # ator final esperado
      actor_reasoning_present: bool    # se deve existir evento actor.reasoning
      review_required: bool            # se deve existir ReviewTask
      event_types: list[string]        # eventos SSE esperados em ordem
      response_contains_any: list[str] # pelo menos uma keyword presente
      response_contains_none: list[str]# nenhuma keyword presente
      tool_calls_include: list[string] # 🆕 nomes de tools que o LLM deve ter chamado (modo live)
      loop_count_min: int              # 🆕 mínimo de loops do agente (benchmark)
      loop_count_max: int              # 🆕 máximo de loops do agente (benchmark)

    evaluation:                        # 🆕 reservado para melhoria 04 (LLM-as-Judge)
      # Não implementar agora. Estrutura planejada:
      # metrics: [faithfulness, relevance, safety]
      # reference_answer: string
      # threshold: float
```

### Campos novos — justificativa

| Campo | Por quê |
|---|---|
| `input.attachments` | Migrar `product-image`, `document-pdf` e `invalid-attachment` que enviam arquivos |
| `expected.http_status` | O cenário `invalid-attachment` espera HTTP 400, não 202 |
| `expected.error_contains` | Validar a mensagem de erro ("Unsupported file type") |
| `expected.tool_calls_include` | Em modo live, confirmar que o LLM escolheu a tool certa (ex: `faq_lookup`, `stock_lookup`) |
| `expected.loop_count_min/max` | Diferenciar comportamento entre arquiteturas no benchmark (swarm faz mais loops que centralized) |
| `evaluation` | Placeholder para deepeval/LLM-as-Judge — não implementar nesta melhoria |

---

## 5. Exemplo Completo — 2 Suites

### 5.1 `scenarios/pharmacy.yaml`

```yaml
suite: pharmacy
description: >
  Cenários de atendimento farmacêutico — FAQ, estoque, revisão humana,
  interação medicamentosa e multi-turn.

defaults:
  architectures:
    - centralized_orchestration
    - structured_workflow
    - decentralized_swarm
  timeout_seconds: 60

cases:
  # ── Migrado de faq-question.json ──────────────────────────────────
  - id: faq_horario_funcionamento
    input:
      text: "Qual o horario de funcionamento da farmacia hoje?"
    expected:
      route: faq
      final_actor: faq_agent
      review_required: false
      event_types:
        - processing.started
        - response.final
        - processing.completed
      response_contains_any:
        - horário
        - horario
        - funcionamento
        - "[modo mock]"
      response_contains_none:
        - "{''"
      tool_calls_include:            # 🆕 modo live
        - faq_lookup

  # ── YAML existente (refinado) ─────────────────────────────────────
  - id: dipirona_dor_de_cabeca
    input:
      text: "Posso tomar dipirona pra dor de cabeça?"
    expected:
      route: faq
      final_actor: supervisor_agent
      actor_reasoning_present: true
      event_types:
        - processing.started
        - actor.reasoning
        - response.final
        - processing.completed
      response_contains_any:
        - farmacêutico
        - farmaceutico
        - médico
        - medico
        - profissional
        - "[modo mock]"
      response_contains_none:
        - "{''"
        - "{ '"
        - "Supervisor central concluiu"
      tool_calls_include:            # 🆕 modo live
        - faq_lookup

  # ── Migrado de stock-availability.json ────────────────────────────
  - id: consulta_estoque_dipirona
    input:
      text: "Tem dipirona em estoque?"
    expected:
      route: stock_lookup
      final_actor: stock_agent
      review_required: false
      event_types:
        - processing.started
        - response.final
        - processing.completed
      response_contains_any:
        - estoque
        - disponível
        - disponivel
        - "[modo mock]"
      tool_calls_include:            # 🆕 modo live
        - stock_lookup

  # ── Migrado de human-review-needed.json ───────────────────────────
  - id: revisao_humana_forcada
    input:
      text: "Preciso que um supervisor faca revisao humana deste atendimento."
    message_metadata:
      forceReview: true              # força review via metadata
    expected:
      route: faq
      final_actor: faq_agent
      review_required: true
      event_types:
        - processing.started
        - review.required
        - response.final
        - processing.completed

  # ── NOVO: interação medicamentosa ─────────────────────────────────
  - id: interacao_medicamentosa
    input:
      text: "Estou tomando varfarina e quero tomar ibuprofeno junto, pode?"
    expected:
      route: faq
      actor_reasoning_present: true
      review_required: true          # interação perigosa → review gate
      event_types:
        - processing.started
        - actor.reasoning
        - review.required
        - response.final
        - processing.completed
      response_contains_any:
        - interação
        - interacao
        - contraindicado
        - médico
        - medico
        - farmacêutico
        - "[modo mock]"
      response_contains_none:
        - "pode sim"
        - "sem problemas"
      tool_calls_include:            # 🆕 modo live
        - faq_lookup
    message_metadata:
      forceReview: true              # garante review mesmo em mock

  # ── NOVO: multi-turn para testar swarm ────────────────────────────
  - id: multi_turn_swarm
    input:
      text: "Quero saber se tem paracetamol em estoque e também qual a dosagem recomendada para adultos."
    expected:
      route: faq                     # rota primária (mock roteia tudo para faq)
      event_types:
        - processing.started
        - response.final
        - processing.completed
      response_contains_any:
        - paracetamol
        - dosagem
        - estoque
        - "[modo mock]"
      loop_count_min: 1              # 🆕 centralized: 1 loop
      loop_count_max: 5              # 🆕 swarm: pode fazer até 5 loops
      tool_calls_include:            # 🆕 modo live — ambas as tools
        - faq_lookup
        - stock_lookup
```

### 5.2 `scenarios/attachments.yaml`

```yaml
suite: attachments
description: >
  Cenários com upload de arquivos — imagem de produto, documento PDF
  e anexo inválido (caso de erro).

defaults:
  architectures:
    - centralized_orchestration
    - structured_workflow
    - decentralized_swarm
  timeout_seconds: 60

cases:
  # ── Migrado de product-image.json ─────────────────────────────────
  - id: imagem_produto
    input:
      text: "Consegue identificar este produto pela imagem?"
      attachments:                   # 🆕 multipart upload
        - path: packages/test-fixtures/assets/tiny-product.png.base64
          mime_type: image/png
    expected:
      route: image_intake
      final_actor: image_intake_agent
      review_required: false
      event_types:
        - processing.started
        - response.final
        - processing.completed
      response_contains_any:
        - imagem
        - produto
        - "[modo mock]"
      tool_calls_include:            # 🆕 modo live
        - attachment_intake

  # ── Migrado de document-pdf.json ──────────────────────────────────
  - id: documento_pdf
    input:
      text: "Segue um documento para analise simulada."
      attachments:                   # 🆕 multipart upload
        - path: packages/test-fixtures/assets/tiny-document.pdf.base64
          mime_type: application/pdf
    expected:
      route: image_intake
      final_actor: image_intake_agent
      review_required: false
      event_types:
        - processing.started
        - response.final
        - processing.completed
      response_contains_any:
        - documento
        - análise
        - analise
        - "[modo mock]"
      tool_calls_include:            # 🆕 modo live
        - attachment_intake

  # ── Migrado de invalid-attachment.json ────────────────────────────
  - id: anexo_invalido
    input:
      text: "Estou anexando um arquivo invalido de proposito."
      attachments:                   # 🆕 multipart upload
        - path: packages/test-fixtures/assets/not-an-image.txt
          mime_type: text/plain
    expected:
      http_status: 400               # 🆕 espera rejeição
      error_contains: "Unsupported file type"  # 🆕 mensagem de erro
```

---

## 6. Implementação Passo a Passo

### 6a. Estender `api_client.py` — suporte a attachments

Alterar `send_message` para aceitar `attachments: list[tuple[Path, str]]` e fazer multipart upload real:

```python
# api_client.py — assinatura estendida
def send_message(
    self,
    conversation_id: str,
    text: str,
    metadata: dict | None = None,
    attachments: list[tuple[Path, str]] | None = None,  # 🆕
    expected_status: int = 202,                          # 🆕
) -> dict:
    files = []
    if attachments:
        for file_path, mime_type in attachments:
            files.append(("files", (file_path.name, file_path.read_bytes(), mime_type)))

    resp = self._http.post(
        "/messages",
        data={
            "conversationId": conversation_id,
            "text": text,
            "metadata_json": json.dumps(metadata or {}),
        },
        files=files or None,
    )
    assert resp.status_code == expected_status, (
        f"Expected {expected_status}, got {resp.status_code}: {resp.text}"
    )
    return resp.json() if resp.status_code < 400 else {"error": resp.text}
```

### 6b. Estender `conftest.py` — novos campos do schema

Na função `_load_scenarios`, propagar os novos campos para cada `case`:

- Ler `input.attachments` e resolver paths relativos à raiz do repo.
- Propagar `expected.http_status` (default `202`).
- Propagar `expected.error_contains`, `tool_calls_include`, `loop_count_min`, `loop_count_max`.

### 6c. Estender `test_e2e.py` — novas asserções

Adicionar ao `test_scenario`:

```python
# Após envio da mensagem — tratar http_status != 202
expected_status = expected.get("http_status", 202)
if expected_status >= 400:
    error_text = msg_resp.get("error", "")
    error_kw = expected.get("error_contains")
    if error_kw and error_kw not in error_text:
        _fail(f"Expected error containing '{error_kw}', got: {error_text}")
    return  # cenário de erro — não esperar eventos SSE

# Após coletar eventos — tool_calls_include
expected_tools = expected.get("tool_calls_include", [])
if expected_tools:
    conv_data = api_client.get_conversation(conversation_id)
    events = conv_data.get("events", [])
    called_tools = {
        e.get("payload", {}).get("toolName")
        for e in events
        if e.get("eventType") in ("tool.invoked", "tool.completed")
    }
    for tool in expected_tools:
        if tool not in called_tools:
            _fail(f"Expected tool '{tool}' to be called, but only found: {called_tools}")

# loop_count assertions
loop_min = expected.get("loop_count_min")
loop_max = expected.get("loop_count_max")
if loop_min is not None or loop_max is not None:
    conv_data = api_client.get_conversation(conversation_id)
    events = conv_data.get("events", [])
    loop_count = sum(1 for e in events if e.get("eventType") == "actor.invoked")
    if loop_min is not None and loop_count < loop_min:
        _fail(f"Expected at least {loop_min} loops, got {loop_count}")
    if loop_max is not None and loop_count > loop_max:
        _fail(f"Expected at most {loop_max} loops, got {loop_count}")
```

### 6d. Criar os YAMLs

1. Criar `tests/e2e-quality/scenarios/pharmacy.yaml` com o conteúdo da [seção 5.1](#51-scenariospharmacyyaml).
2. Criar `tests/e2e-quality/scenarios/attachments.yaml` com o conteúdo da [seção 5.2](#52-scenariosattachmentsyaml).

### 6e. Deprecar JSON fixtures

Adicionar `packages/test-fixtures/scenarios/README.md`:

```markdown
# ⚠️ DEPRECATED

Estes cenários JSON foram migrados para o framework e2e-quality em YAML.

**Nova localização:** `tests/e2e-quality/scenarios/`

Os arquivos JSON são mantidos temporariamente porque `scripts/run_fixture_scenarios.py`
ainda os consome. Em uma iteração futura, o script será reescrito para ler do YAML
e estes arquivos serão removidos.
```

### 6f. Adicionar cenários novos

Os 2 cenários novos (`interacao_medicamentosa` e `multi_turn_swarm`) já estão incluídos no YAML da seção 5.1. Detalhes:

- **`interacao_medicamentosa`**: Varfarina + ibuprofeno é uma interação perigosa real. O cenário usa `forceReview: true` em `message_metadata` para garantir que o review gate é acionado mesmo em modo mock.
- **`multi_turn_swarm`**: Pergunta composta (estoque + dosagem) que exercita a capacidade do swarm de decompor em sub-tarefas. `loop_count_min/max` permite diferenciar comportamento entre arquiteturas.

---

## 7. Como Validar

### 7.1 Modo Mock (`ENABLE_LIVE_LLM=false`)

```bash
make test-quality
```

Resultado esperado:
- **8 cenários × 3 arquiteturas = 24 testes** (menos `anexo_invalido` que não varia por arquitetura = **21 + 3 = 24**).
- Todos passam com `route=faq` e `"[modo mock]"` na resposta.
- `anexo_invalido` retorna HTTP 400 com `"Unsupported file type"`.
- `revisao_humana_forcada` e `interacao_medicamentosa` criam `ReviewTask`.

### 7.2 Modo Live (`ENABLE_LIVE_LLM=true`)

```bash
ENABLE_LIVE_LLM=true make test-quality
```

Validações adicionais:
- Cada cenário roteia para a tool correta via `tool_calls_include`:
  - FAQ → `faq_lookup`
  - Estoque → `stock_lookup`
  - Imagem/PDF → `attachment_intake`
- `response_contains_any` valida que a resposta do LLM é relevante.
- `response_contains_none` garante que não há artefatos de debug.

### 7.3 Com Diferenciação de Arquiteturas (melhoria 01)

Se a melhoria 01 estiver pronta:

```bash
ENABLE_LIVE_LLM=true make test-quality
```

- `loop_count_min/max` no cenário `multi_turn_swarm` diferencia:
  - `centralized_orchestration`: 1-2 loops (orquestrador único)
  - `decentralized_swarm`: 3-5 loops (agentes colaborando)

---

## 8. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| JSON fixtures dependem de fluxos que o mock não emite (ex: `review.required` events) | Cenários de review falham em mock | Usar `forceReview: true` em `message_metadata` — o `processing_dispatcher` já suporta esse flag |
| `invalid-attachment` é um caso de erro HTTP que o schema YAML não cobria | Cenário não pode ser migrado | Adicionar `http_status: 400` + `error_contains` ao schema (seção 4) |
| Scripts legados (`run_fixture_scenarios.py`) quebram se deletarmos os JSONs | Regressão em validação manual | Manter JSONs como deprecated; adicionar README apontando para YAML; remover em iteração futura |
| Assets de attachment (`.base64`, `.txt`) precisam existir no disco para multipart upload | Testes falham se path estiver errado | Resolver paths relativos à raiz do repo em `conftest.py`; validar existência antes de rodar |
| `tool_calls_include` só funciona em modo live | Asserção falha em mock (nenhuma tool é chamada) | Condicionar a asserção: só validar se `ENABLE_LIVE_LLM=true` ou se eventos `tool.*` existirem |
| `loop_count_min/max` depende de eventos `actor.invoked` que o mock pode não emitir com granularidade | Contagem incorreta | Tratar como asserção soft: só validar se pelo menos 1 evento `actor.invoked` existir |

---

## 9. Critérios de Pronto

- [ ] **6+ cenários em YAML** — mínimo 8 (6 migrados + 2 novos)
- [ ] **3 arquiteturas** rodam todos os cenários via `make test-quality`
- [ ] **Report do benchmark** (melhoria 02) consome os YAMLs como fonte de cenários
- [ ] **JSON antigos** marcados como deprecated com README
- [ ] **`api_client.py`** suporta multipart upload com attachments
- [ ] **`conftest.py`** resolve `input.attachments` e propaga novos campos
- [ ] **`test_e2e.py`** valida `http_status`, `error_contains`, `tool_calls_include`, `loop_count_*`
- [ ] **Documentação** atualizada em `docs/testing/e2e-quality-framework.md` com o schema estendido

---

## 10. Fora de Escopo

- **deepeval / LLM-as-Judge** — o bloco `evaluation` é reservado mas não implementado (melhoria 04).
- **Dashboard de observabilidade** — não mexer (melhoria 05).
- **Diferenciação real de arquiteturas** — os 3 modos rodam mas produzem resultado idêntico em mock (melhoria 01).
- **Reescrita de `run_fixture_scenarios.py`** — manter funcional com JSONs deprecated; reescrever em iteração futura.
- **CI/CD** — rodar `make test-quality` em pipeline fica para depois.

---

## Referências

| Recurso | Caminho |
|---|---|
| JSON fixtures (deprecated) | `packages/test-fixtures/scenarios/*.json` |
| Assets de teste | `packages/test-fixtures/assets/` |
| YAML scenarios (novo) | `tests/e2e-quality/scenarios/` |
| Framework e2e-quality | `docs/testing/e2e-quality-framework.md` |
| API client | `tests/e2e-quality/api_client.py` |
| Conftest | `tests/e2e-quality/conftest.py` |
| Test runner | `tests/e2e-quality/test_e2e.py` |
| Script legado | `scripts/run_fixture_scenarios.py` |
| Benchmark script | `scripts/run_architecture_benchmark.py` |
