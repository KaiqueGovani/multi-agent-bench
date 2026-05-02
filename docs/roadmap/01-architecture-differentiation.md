# 01 — Diferenciação Real das Arquiteturas

> **Plano de refatoração para que centralized / workflow / swarm se comportem de forma fundamentalmente diferente em modo live, viabilizando a comparação experimental do TCC.**

---

## Sumário

1. [Contexto e Motivação](#1-contexto-e-motivação)
2. [Estado Atual](#2-estado-atual)
3. [Estado Desejado](#3-estado-desejado)
4. [Design Técnico](#4-design-técnico)
5. [Eventos Esperados por Arquitetura](#5-eventos-esperados-por-arquitetura)
6. [Implementação Passo a Passo](#6-implementação-passo-a-passo)
7. [Como Validar](#7-como-validar)
8. [Riscos e Mitigações](#8-riscos-e-mitigações)
9. [Critérios de Pronto](#9-critérios-de-pronto)
10. [Fora de Escopo](#10-fora-de-escopo)

---

## 1. Contexto e Motivação

O objetivo central do TCC é **comparar arquiteturas de coordenação multi-agente** — orquestração centralizada, workflow estruturado e swarm descentralizado — num cenário real de atendimento farmacêutico. Para que essa comparação tenha validade experimental, cada arquitetura precisa produzir **padrões de execução observavelmente distintos**: número de agentes envolvidos, sequência de eventos, contagem de tool calls, latência e número de handoffs.

Hoje, as três arquiteturas são **rótulos visuais** sobre a mesma execução. Em modo live (LLM ativo), todas chamam `ctx.invoke_live_supervisor()` com os mesmos 3 tools e um único `Agent` Strands. A única diferença são strings de system prompt e nomes de atores nos eventos emitidos. Isso invalida qualquer análise comparativa: não há divergência real de comportamento para medir.

Este documento descreve **o que cada arquitetura deve fazer**, como refatorar o código para atingir essa diferenciação, e como validar que a divergência é real e mensurável.

---

## 2. Estado Atual

### 2.1 O problema: `_execute_live` é idêntico nas 3 arquiteturas

Todas as três implementações seguem exatamente o mesmo padrão em `_execute_live`:

1. Importam os mesmos 3 tools: `faq_lookup`, `stock_lookup`, `attachment_intake`
2. Emitem um único evento `actor.reasoning`
3. Chamam `ctx.invoke_live_supervisor()` com os mesmos 3 tools
4. Fazem fallback para `_execute_mock` se o resultado for `None`
5. Usam `_infer_route_from_tools` + `_detect_review_required_in_text` (ambas importadas de `centralized.py`)
6. Emitem `response.final` + `run.completed`

**`centralized.py:37–60`** — supervisor com 3 tools:

```python
def _execute_live(self, ctx: ExecutionContext, text: str) -> ExecutionResult:
    from app.tools.domain_tools import faq_lookup, stock_lookup, attachment_intake

    system_prompt = (
        "Você é um supervisor de atendimento de uma farmácia. Dado a mensagem do usuário, "
        "você decide qual ferramenta usar (faq_lookup, stock_lookup, ou attachment_intake) "
        "e compoe a resposta final em português do Brasil, em prosa corrida. ..."
    )
    # ...
    result = ctx.invoke_live_supervisor(
        system_prompt=system_prompt,
        user_message=text,
        tools=[faq_lookup, stock_lookup, attachment_intake],
    )
```

**`workflow.py:27–54`** — mesmo padrão, apenas muda o prompt e o actor name:

```python
def _execute_live(self, ctx: ExecutionContext, text: str) -> ExecutionResult:
    from app.tools.domain_tools import faq_lookup, stock_lookup, attachment_intake

    system_prompt = (
        "Você é um pipeline estruturado de atendimento de farmácia. ..."
    )
    # ...
    result = ctx.invoke_live_supervisor(
        system_prompt=system_prompt,
        user_message=text,
        tools=[faq_lookup, stock_lookup, attachment_intake],
        supervisor_actor="workflow_synthesizer",
    )
```

**`swarm.py:27–54`** — idem:

```python
def _execute_live(self, ctx: ExecutionContext, text: str) -> ExecutionResult:
    from app.tools.domain_tools import faq_lookup, stock_lookup, attachment_intake

    system_prompt = (
        "Você faz parte de um swarm descentralizado de atendimento de farmácia. ..."
    )
    # ...
    result = ctx.invoke_live_supervisor(
        system_prompt=system_prompt,
        user_message=text,
        tools=[faq_lookup, stock_lookup, attachment_intake],
        supervisor_actor="swarm_synthesizer",
    )
```

### 2.2 Diferenças reais (apenas cosméticas)

| Aspecto | Centralized | Workflow | Swarm |
|---------|-------------|----------|-------|
| Persona no prompt | "supervisor de atendimento" | "pipeline estruturado" | "swarm descentralizado" |
| `actor_name` no reasoning | `supervisor_agent` | `workflow_synthesizer` | `swarm_synthesizer` |
| `supervisor_actor` kwarg | default (`supervisor_agent`) | `workflow_synthesizer` | `swarm_synthesizer` |
| `architecture_mode` string | `centralized_orchestration` | `structured_workflow` | `decentralized_swarm` |

**Veredicto:** a lógica de execução, o conjunto de tools e a invocação do LLM são 100% idênticos. A diferenciação existe apenas no modo mock (`_execute_mock`), que já implementa padrões de eventos distintos mas não usa LLM.

---

## 3. Estado Desejado

### 3.1 Tabela comparativa

| Dimensão | Centralized | Workflow | Swarm |
|----------|-------------|----------|-------|
| **Nº de Agents Strands** | 1 (supervisor) | 5–6 (um por estágio) | 4–5 (coordinator + specialists + synthesizer) |
| **Tools por agente** | 3 (todos) | 0–1 (escopo mínimo) | 1 + `handoff_to_peer` |
| **Padrão de eventos** | 1× `actor.reasoning` → N× `tool.*` → 1× `response.final` | N× `node.started` → `actor.reasoning` → `tool.*` → `node.completed` (por estágio) | N× `actor.reasoning` + N× `handoff.requested` + N× `actor.message` |
| **`loop_count` esperado** | 0 | ≥ número de estágios executados (4–5) | ≥ 2 (hops entre peers) |
| **`tool_call_count` esperado** | 1–2 | 1–2 (apenas no estágio de evidência) | 1–2 (no specialist que atende) |
| **`handoff_count` esperado** | 0 | 0 | ≥ 2 |
| **Latência relativa** | 1× (baseline) | ~2–3× (múltiplas chamadas LLM sequenciais) | ~2–4× (hops entre agents) |
| **Topologia** | Estrela (supervisor no centro) | Pipeline linear | Malha peer-to-peer |

---

## 4. Design Técnico

### 4.1 Centralized Orchestration — Supervisor Único

Esta é a arquitetura mais próxima do estado atual. Um único `Agent` Strands recebe **todos** os tools e decide autonomamente qual usar.

**Agentes envolvidos:** 1 — `supervisor_agent`

**Tools disponíveis:** `faq_lookup`, `stock_lookup`, `attachment_intake` (os 3)

**Como Strands é usado:** uma única instância de `Agent` com `tools=[faq_lookup, stock_lookup, attachment_intake]`. O LLM decide qual tool chamar com base no conteúdo da mensagem. Os hooks `BeforeToolCallEvent` / `AfterToolCallEvent` já instrumentam cada chamada.

**System prompt estratégico:**

```
Você é o supervisor de atendimento de uma farmácia. Você é o ÚNICO agente
responsável por toda a interação. Analise a mensagem do usuário e decida:

1. Se é uma pergunta genérica (horário, entrega, devolução, pagamento) → use faq_lookup
2. Se pergunta sobre disponibilidade de um produto → use stock_lookup
3. Se o usuário enviou anexos (imagem, PDF) → use attachment_intake PRIMEIRO

Após coletar a informação, componha a resposta final em português do Brasil,
em prosa corrida. Se a pergunta for clínica (dosagem, interação, efeito
colateral, gestação), SEMPRE recomende consultar um farmacêutico ou médico.
Nunca forneça dosagens específicas.
```

**Refatoração necessária:** mínima. O `_execute_live` atual já implementa esse padrão. Ajustes:
- Tornar o system prompt mais explícito sobre o papel de "agente único"
- Garantir que `loop_count` permaneça 0 (sem loops, decisão direta)
- Emitir exatamente 1 evento `actor.reasoning` antes da decisão de tool

### 4.2 Structured Workflow — Pipeline Determinístico

A mudança mais significativa. Em vez de um único Agent, o workflow cria **múltiplos Agents Strands**, cada um com escopo mínimo, executados em sequência determinística.

**Agentes envolvidos:** 5–6

| Agente | Tools | Responsabilidade |
|--------|-------|------------------|
| `router_agent` | nenhum | Classifica a intenção → retorna label de rota (`faq`, `stock_lookup`, `image_intake`) |
| `faq_agent` | `faq_lookup` | Coleta evidência de FAQ |
| `stock_agent` | `stock_lookup` | Coleta evidência de estoque |
| `image_intake_agent` | `attachment_intake` | Analisa anexos |
| `review_agent` | nenhum | Verifica se a resposta requer revisão humana (keywords + política) |
| `synthesis_agent` | nenhum | Compõe a resposta final em prosa a partir das evidências coletadas |

**Pipeline:** `classify → gather_evidence → (optional) multimodal_analysis → review_gate → synthesize`

**Como Strands é usado:** múltiplas instâncias de `Agent`, cada uma criada com `system_prompt` e `tools` específicos. O código Python orquestra a sequência — não o LLM.

**System prompts estratégicos:**

**router_agent:**
```
Você é um classificador de intenções para atendimento farmacêutico.
Dada a mensagem do usuário, retorne APENAS uma das seguintes labels:
- "faq" — para perguntas genéricas (horário, entrega, devolução, pagamento, etc.)
- "stock_lookup" — para perguntas sobre disponibilidade ou preço de produtos
- "image_intake" — se o usuário enviou anexos (imagens ou documentos)

Responda SOMENTE com a label, sem explicação adicional.
```

**faq_agent:**
```
Você é um especialista em FAQ de farmácia. Use a ferramenta faq_lookup para
buscar a resposta mais relevante. Retorne o resultado da ferramenta sem
modificação. Não invente informações.
```

**stock_agent:**
```
Você é um especialista em consulta de estoque. Use a ferramenta stock_lookup
para verificar a disponibilidade do produto mencionado. Retorne o resultado
da ferramenta sem modificação.
```

**review_agent:**
```
Você é um revisor de conformidade farmacêutica. Analise a evidência coletada
e a pergunta original. Responda APENAS "review_required: true" ou
"review_required: false". Marque true se:
- A pergunta envolve dosagem, interação medicamentosa, efeito colateral ou gestação
- O produto é controlado (ex: rivotril, insulina)
- A evidência é insuficiente para uma resposta segura
```

**synthesis_agent:**
```
Você é o sintetizador final do atendimento farmacêutico. Receba a evidência
coletada pelos agentes anteriores e componha uma resposta em português do
Brasil, em prosa corrida. Seja claro e objetivo. Se review_required=true,
inclua a recomendação de consultar um farmacêutico ou médico.
Nunca forneça dosagens específicas.
```

**Sketch de implementação (pseudo-código):**

```python
def _execute_live(self, ctx, text):
    # Stage 1: Classify
    ctx.emit("node", "started", "running", actor_name="router_agent", ...)
    router = Agent(model=model, system_prompt=ROUTER_PROMPT, tools=[])
    route_label = str(router(text)).strip()  # "faq" | "stock_lookup" | "image_intake"
    ctx.emit_reasoning("router_agent", "workflow.classify", thought=..., decision=route_label)
    ctx.emit("node", "completed", "completed", actor_name="router_agent", ...)
    ctx.loop_count += 1

    # Stage 2: Gather evidence (agent escolhido pela rota)
    ctx.emit("node", "started", "running", actor_name=evidence_actor, ...)
    evidence_agent = Agent(model=model, system_prompt=EVIDENCE_PROMPT, tools=[selected_tool])
    evidence = str(evidence_agent(text))
    ctx.emit("node", "completed", "completed", actor_name=evidence_actor, ...)
    ctx.loop_count += 1

    # Stage 3 (optional): Multimodal — só se houver anexos
    if ctx.request.latest_message.attachments:
        ctx.emit("node", "started", "running", actor_name="image_intake_agent", ...)
        image_agent = Agent(model=model, system_prompt=IMAGE_PROMPT, tools=[attachment_intake])
        multimodal_evidence = str(image_agent(text))
        ctx.emit("node", "completed", "completed", actor_name="image_intake_agent", ...)
        ctx.loop_count += 1

    # Stage 4: Review gate
    ctx.emit("node", "started", "running", actor_name="review_agent", ...)
    review = Agent(model=model, system_prompt=REVIEW_PROMPT, tools=[])
    review_result = str(review(f"Pergunta: {text}\nEvidência: {evidence}"))
    review_required = "true" in review_result.lower()
    ctx.emit("node", "completed", "completed", actor_name="review_agent", ...)
    ctx.loop_count += 1

    # Stage 5: Synthesize
    ctx.emit("node", "started", "running", actor_name="synthesis_agent", ...)
    synth = Agent(model=model, system_prompt=SYNTHESIS_PROMPT, tools=[])
    final_text = str(synth(f"Evidência: {evidence}\nReview: {review_required}"))
    ctx.emit("node", "completed", "completed", actor_name="synthesis_agent", ...)
    ctx.loop_count += 1

    ctx.emit_final(final_text, route=route_label, ...)
    return ctx.build_result(final_text, review_required)
```

### 4.3 Decentralized Swarm — Peer-to-Peer com Handoff

A arquitetura mais complexa. Múltiplos `Agent` Strands que podem **delegar entre si** via uma tool `handoff_to_peer`. Cada agente tem autonomia para decidir se resolve a query ou passa para outro peer.

**Agentes envolvidos:** 4–5

| Agente | Tools | Responsabilidade |
|--------|-------|------------------|
| `swarm_coordinator` | `handoff_to_peer` | Recebe a query, decide qual specialist invocar |
| `faq_specialist` | `faq_lookup`, `handoff_to_peer` | Responde FAQs; pode delegar para outro peer |
| `stock_specialist` | `stock_lookup`, `handoff_to_peer` | Consulta estoque; pode delegar |
| `image_specialist` | `attachment_intake`, `handoff_to_peer` | Analisa anexos; pode delegar |
| `swarm_synthesizer` | nenhum | Recebe evidências acumuladas e compõe resposta final |

**Como Strands é usado:** múltiplas instâncias de `Agent`. A tool `handoff_to_peer` é uma função Python que, quando chamada pelo LLM, **invoca programaticamente outro Agent** e retorna o resultado. Isso cria uma cadeia de chamadas peer-to-peer.

**Guardrail:** `runtime_max_handoffs=6` (já configurado em `config.py:30`). Cada chamada a `handoff_to_peer` incrementa um contador; se exceder o limite, a tool retorna erro e força o agente atual a sintetizar a resposta.

**System prompts estratégicos:**

**swarm_coordinator:**
```
Você é o coordenador de um swarm de atendimento farmacêutico. Você NÃO
responde diretamente ao usuário. Sua função é analisar a mensagem e
delegar para o especialista correto usando handoff_to_peer:
- "faq_specialist" — para perguntas genéricas
- "stock_specialist" — para consultas de estoque/disponibilidade
- "image_specialist" — se houver anexos

Sempre use handoff_to_peer com o nome do peer e o motivo da delegação.
```

**faq_specialist:**
```
Você é um especialista em FAQ de farmácia dentro de um swarm colaborativo.
Use faq_lookup para buscar informações. Se a pergunta também envolver
estoque, use handoff_to_peer("stock_specialist", "complementar com dados
de estoque"). Caso contrário, retorne sua resposta diretamente.
```

**stock_specialist:**
```
Você é um especialista em estoque dentro de um swarm colaborativo.
Use stock_lookup para consultar disponibilidade. Se precisar de contexto
adicional de FAQ, use handoff_to_peer("faq_specialist", "complementar
com informações gerais"). Caso contrário, retorne sua resposta.
```

**Implementação do handoff (sketch):**

```python
# Em swarm.py — factory que cria a tool handoff_to_peer com closure sobre o contexto

def _make_handoff_tool(ctx: ExecutionContext, agents: dict[str, Agent], handoff_count: list[int]):
    """Cria a tool handoff_to_peer com acesso ao registry de agents e ao contexto."""

    @tool()
    def handoff_to_peer(peer_name: str, reason: str) -> dict:
        """Delega a execução para outro agente do swarm. Use quando precisar
        de um especialista diferente para complementar a resposta."""

        if handoff_count[0] >= ctx.settings.runtime_max_handoffs:
            return {
                "error": "max_handoffs_exceeded",
                "message": f"Limite de {ctx.settings.runtime_max_handoffs} handoffs atingido. "
                           "Sintetize a resposta com as informações disponíveis.",
            }

        peer = agents.get(peer_name)
        if peer is None:
            return {"error": "unknown_peer", "message": f"Agente '{peer_name}' não encontrado."}

        handoff_count[0] += 1
        ctx.loop_count += 1
        ctx.emit(
            "handoff", "requested", "running",
            actor_name="current_agent",
            node_id=f"swarm.handoff.{handoff_count[0]}",
            payload={"from": "current", "to": peer_name, "reason": reason, "hop": handoff_count[0]},
        )

        # Invoca o peer Agent programaticamente
        ctx.emit("node", "started", "running", actor_name=peer_name, ...)
        peer_result = str(peer(f"Contexto delegado: {reason}"))
        ctx.emit_message(peer_name, f"swarm.{peer_name}.message", peer_result[:200])
        ctx.emit("node", "completed", "completed", actor_name=peer_name, ...)

        return {"peer": peer_name, "result": peer_result}

    return handoff_to_peer


def _execute_live(self, ctx, text):
    # Cria os agents especializados
    faq_spec = Agent(model=model, system_prompt=FAQ_SPEC_PROMPT, tools=[faq_lookup, handoff_tool])
    stock_spec = Agent(model=model, system_prompt=STOCK_SPEC_PROMPT, tools=[stock_lookup, handoff_tool])
    image_spec = Agent(model=model, system_prompt=IMAGE_SPEC_PROMPT, tools=[attachment_intake, handoff_tool])
    synthesizer = Agent(model=model, system_prompt=SYNTH_PROMPT, tools=[])

    agents = {
        "faq_specialist": faq_spec,
        "stock_specialist": stock_spec,
        "image_specialist": image_spec,
        "swarm_synthesizer": synthesizer,
    }

    handoff_count = [0]
    handoff_tool = _make_handoff_tool(ctx, agents, handoff_count)

    # Coordinator inicia a cadeia
    coordinator = Agent(
        model=model,
        system_prompt=COORDINATOR_PROMPT,
        tools=[handoff_tool],
    )

    ctx.emit_reasoning("swarm_coordinator", "swarm.dispatch", ...)
    coordinator_result = str(coordinator(text))

    # Se o coordinator não delegou, usa o resultado direto
    # Se delegou, o resultado já contém a resposta do peer chain
    final_text = coordinator_result
    review_required = _detect_review_required_in_text(final_text)

    ctx.emit_final(final_text, route=..., final_actor="swarm_synthesizer", ...)
    return ctx.build_result(final_text, review_required)
```

> **Nota:** a tool `handoff_to_peer` precisa ser criada **antes** dos agents que a usam, mas os agents precisam estar no dict para o handoff funcionar. Resolver com lazy initialization ou passando o dict por referência (já que é mutável).

---

## 5. Eventos Esperados por Arquitetura

### 5.1 Centralized Orchestration

Timeline ideal para uma pergunta como "Tem dipirona disponível?":

```
1. run.started                          (status: running)
2. actor.reasoning  [supervisor_agent]  (thought: "Pergunta sobre estoque → stock_lookup")
3. tool.started     [supervisor_agent]  (tool: stock_lookup, input: {question: "..."})
4. tool.completed   [supervisor_agent]  (tool: stock_lookup, result: {product: "dipirona", ...})
5. response.partial [response_streamer] (preview dos primeiros 160 chars)
6. response.final   [supervisor_agent]  (contentText: "...", route: "stock_lookup")
7. run.completed                        (status: completed)
```

**Características:** exatamente 1 `actor.reasoning`, 1–2 pares `tool.started/completed`, 0 `handoff.requested`. `loop_count = 0`.

### 5.2 Structured Workflow

Timeline ideal para a mesma pergunta:

```
 1. run.started                                (status: running)
 2. node.started    [router_agent]             (stage: classify)
 3. actor.reasoning [router_agent]             (thought: "Estoque → stock_lookup")
 4. node.completed  [router_agent]             (route: stock_lookup)
 5. node.started    [stock_agent]              (stage: gather_evidence)
 6. actor.reasoning [stock_agent]              (thought: "Consultando estoque...")
 7. tool.started    [stock_agent]              (tool: stock_lookup)
 8. tool.completed  [stock_agent]              (result: {product: "dipirona", ...})
 9. node.completed  [stock_agent]              (evidence collected)
10. node.started    [review_agent]             (stage: review_gate)
11. actor.reasoning [review_agent]             (thought: "Sem risco clínico")
12. node.completed  [review_agent]             (review_required: false)
13. node.started    [synthesis_agent]          (stage: synthesize)
14. actor.reasoning [synthesis_agent]          (thought: "Compondo resposta...")
15. node.completed  [synthesis_agent]          (final prose)
16. response.partial [response_streamer]
17. response.final   [synthesis_agent]
18. run.completed
```

**Características:** 4+ `actor.reasoning` (um por estágio), 4+ pares `node.started/completed`, 1 par `tool.started/completed`. `loop_count ≥ 4`. 0 `handoff.requested`.

### 5.3 Decentralized Swarm

Timeline ideal para a mesma pergunta:

```
 1. run.started                                    (status: running)
 2. node.started      [swarm_coordinator]          (stage: handoff_loop)
 3. actor.reasoning   [swarm_coordinator]           (thought: "Estoque → stock_specialist")
 4. handoff.requested [swarm_coordinator]           (to: stock_specialist, reason: "consulta estoque")
 5. node.started      [stock_specialist]            (stage: handoff_loop)
 6. actor.reasoning   [stock_specialist]            (thought: "Usando stock_lookup...")
 7. tool.started      [stock_specialist]            (tool: stock_lookup)
 8. tool.completed    [stock_specialist]            (result: {product: "dipirona", ...})
 9. actor.message     [stock_specialist]            (text: "Dipirona disponível, 17 frascos")
10. node.completed    [stock_specialist]
11. handoff.requested [stock_specialist]            (to: swarm_synthesizer, reason: "sintetizar")
12. node.started      [swarm_synthesizer]           (stage: handoff_loop)
13. actor.reasoning   [swarm_synthesizer]           (thought: "Compondo resposta final...")
14. node.completed    [swarm_synthesizer]
15. response.partial  [response_streamer]
16. response.final    [swarm_synthesizer]
17. run.completed
```

**Características:** 3+ `actor.reasoning`, 2+ `handoff.requested`, 1+ `actor.message`. `loop_count ≥ 2`. Cenários complexos podem ter mais hops (ex: coordinator → stock_specialist → faq_specialist → synthesizer).

---

## 6. Implementação Passo a Passo

### Passo 1 — Extrair factory de Agent para `base.py`

**Arquivo:** `apps/agent-runtime/app/architectures/base.py`
**Hunks estimados:** 1 (novo método `create_agent` em `ExecutionContext`)

Criar um helper `create_agent(system_prompt, tools, actor_name)` que encapsula a criação de `BedrockModel` + `Agent` + hook registration. Isso evita duplicação entre as 3 arquiteturas e centraliza a instrumentação de eventos.

### Passo 2 — Refatorar `centralized.py` (ajuste mínimo)

**Arquivo:** `apps/agent-runtime/app/architectures/centralized.py`
**Hunks estimados:** 1–2

- Substituir a criação manual de `Agent` por `ctx.create_agent(...)`
- Tornar o system prompt mais explícito sobre "agente único"
- Garantir que `loop_count` permanece 0
- Sem mudança estrutural — esta arquitetura já está próxima do design alvo

### Passo 3 — Reescrever `workflow.py` com pipeline multi-agent

**Arquivo:** `apps/agent-runtime/app/architectures/workflow.py`
**Hunks estimados:** 3–4 (reescrita quase completa de `_execute_live`)

- Criar 5 Agents Strands separados via `ctx.create_agent()`
- Implementar o pipeline sequencial: classify → evidence → (multimodal) → review → synthesize
- Cada estágio emite `node.started` / `node.completed`
- Incrementar `ctx.loop_count` a cada estágio
- O `router_agent` retorna structured output (label de rota)
- O agent de evidência é selecionado pela rota (faq_agent / stock_agent / image_intake_agent)
- O `review_agent` faz policy check sem tools
- O `synthesis_agent` compõe a resposta final sem tools

### Passo 4 — Reescrever `swarm.py` com handoff peer-to-peer

**Arquivo:** `apps/agent-runtime/app/architectures/swarm.py`
**Hunks estimados:** 4–5 (reescrita completa de `_execute_live`)

- Criar a tool `handoff_to_peer` como closure com acesso ao registry de agents e ao `ExecutionContext`
- Criar 4–5 Agents Strands: coordinator, faq_specialist, stock_specialist, image_specialist, synthesizer
- Cada specialist tem sua domain tool + `handoff_to_peer`
- O coordinator tem apenas `handoff_to_peer`
- Implementar guardrail de `runtime_max_handoffs` (ler de `ctx.settings.runtime_max_handoffs`)
- Emitir `handoff.requested` a cada delegação
- Emitir `actor.message` para outputs intermediários dos specialists

### Passo 5 — Adicionar `handoff_count` ao `ExecutionResult`

**Arquivo:** `apps/agent-runtime/app/architectures/base.py`
**Hunks estimados:** 1

- Adicionar campo `handoff_count: int = 0` ao dataclass `ExecutionResult`
- Adicionar contador `self.handoff_count: int = 0` ao `ExecutionContext`
- Propagar para `RunSummary` em `execution.py`

### Passo 6 — Atualizar `_execute_mock` para consistência

**Arquivos:** `centralized.py`, `workflow.py`, `swarm.py`
**Hunks estimados:** 1 por arquivo

- Garantir que o mock emite o mesmo padrão de eventos que o live (mesmos `node.started/completed`, mesmos actor names)
- Isso permite que os testes unitários validem o padrão de eventos sem precisar de LLM

### Passo 7 — Expandir testes unitários

**Arquivo:** `apps/agent-runtime/tests/test_architectures.py`
**Hunks estimados:** 3–4 (novos test cases)

Detalhado na seção 7.

---

## 7. Como Validar

### 7.1 Testes unitários — `test_architectures.py`

O arquivo atual (`apps/agent-runtime/tests/test_architectures.py`) tem 22 test cases (9 smoke × 3 arch + 5 específicos). Expandir para ~35–40 testes com assertions por arquitetura:

**Novos testes para Centralized:**
- `test_centralized_zero_loop_count` — `loop_count == 0`
- `test_centralized_zero_handoffs` — nenhum evento `handoff.requested`
- `test_centralized_single_reasoning` — exatamente 1 evento `actor.reasoning`
- `test_centralized_supervisor_is_final_actor` — `finalActor == "supervisor_agent"`

**Novos testes para Workflow:**
- `test_workflow_loop_count_gte_4` — `loop_count >= 4` (um por estágio)
- `test_workflow_multiple_reasoning_events` — ≥ 3 eventos `actor.reasoning` (router + evidence + review + synthesis)
- `test_workflow_node_started_completed_pairs` — cada `node.started` tem um `node.completed` correspondente
- `test_workflow_router_agent_first_reasoning` — primeiro `actor.reasoning` vem de `router_agent`
- `test_workflow_zero_handoffs` — nenhum evento `handoff.requested`
- `test_workflow_multimodal_stage_with_attachments` — estágio multimodal presente quando há anexos

**Novos testes para Swarm:**
- `test_swarm_handoff_events_emitted` — ≥ 2 eventos `handoff.requested`
- `test_swarm_multiple_reasoning_events` — ≥ 2 eventos `actor.reasoning`
- `test_swarm_coordinator_first_reasoning` — primeiro `actor.reasoning` vem de `swarm_coordinator`
- `test_swarm_max_handoffs_guardrail` — simular cenário que excede `runtime_max_handoffs` e verificar que para
- `test_swarm_handoff_count_in_result` — `handoff_count >= 2` no `ExecutionResult`

### 7.2 Testes E2E — `tests/e2e-quality/`

Adicionar assertions específicas por arquitetura nos cenários existentes:

| Cenário | Centralized | Workflow | Swarm |
|---------|-------------|----------|-------|
| `dipirona-disponibilidade` | `loop_count == 0`, 1 `actor.reasoning` | `loop_count >= 4`, ≥ 3 `actor.reasoning` | `loop_count >= 2`, ≥ 2 `handoff.requested` |
| `horario-farmacia` | `tool_call_count == 1` (faq_lookup) | `tool_call_count == 1`, `router_agent` classifica como "faq" | `tool_call_count == 1`, coordinator delega para `faq_specialist` |
| `imagem-receita` | `tool_call_count >= 1` (attachment_intake) | estágio multimodal presente | `image_specialist` invocado via handoff |

### 7.3 Validação manual

Enviar o cenário "Tem dipirona disponível?" em cada arquitetura via `make test-quality` e comparar:

1. **Event timeline** no frontend — verificar visualmente que os padrões de eventos são distintos
2. **Latência** — swarm deve ser ≥ 1.5× mais lento que centralized (múltiplas chamadas LLM)
3. **Tool call count** — similar entre as 3 (1–2), mas distribuído entre agents diferentes
4. **Loop count** — 0 para centralized, ≥ 4 para workflow, ≥ 2 para swarm

---

## 8. Riscos e Mitigações

| Risco | Impacto | Probabilidade | Mitigação |
|-------|---------|---------------|-----------|
| **Swarm: loops infinitos** | Alto — agentes delegam entre si indefinidamente | Média | Guardrail `runtime_max_handoffs=6` já em `config.py:30`. A tool `handoff_to_peer` retorna erro ao exceder o limite, forçando o agente atual a sintetizar. |
| **Latência excessiva no workflow** | Médio — 5 chamadas LLM sequenciais podem levar >30s | Alta | Usar modelo rápido (Haiku) para estágios simples (router, review). Timeout global de `runtime_timeout_seconds=45` já configurado. |
| **LLM confuso com tool-use em swarm** | Médio — o LLM pode não entender quando usar `handoff_to_peer` vs domain tool | Média | System prompts extremamente explícitos. Cada specialist tem no máximo 2 tools. Fallback para centralized em caso de erro. |
| **Regressão nos testes mock** | Baixo — mudanças no `_execute_live` podem quebrar o mock | Baixa | Manter `_execute_mock` separado e estável. Testes unitários rodam em mock por padrão. |
| **Inconsistência de eventos entre mock e live** | Médio — padrões de eventos diferentes entre os dois modos | Média | Passo 6 da implementação: alinhar mock com live nos mesmos actor names e event patterns. |
| **Custo de tokens** | Baixo — múltiplas chamadas LLM por request | Média | Usar Haiku (barato) para estágios intermediários. Monitorar `total_tokens` no `RunSummary`. |

---

## 9. Critérios de Pronto

- [ ] **3 padrões de eventos distintos** observáveis na event timeline do frontend:
  - Centralized: 1 reasoning → tools → final
  - Workflow: N× (node.started → reasoning → tool → node.completed) → final
  - Swarm: N× (reasoning → handoff → reasoning) → final
- [ ] **Latência relativa:** swarm ≥ 1.5× centralized no cenário "dipirona" (medido via `total_duration_ms` no `RunSummary`)
- [ ] **Métricas distintas no `RunSummary`:**
  - `loop_count`: 0 (centralized), ≥ 4 (workflow), ≥ 2 (swarm)
  - `handoff_count`: 0 (centralized e workflow), ≥ 2 (swarm)
  - `tool_call_count`: similar (~1–2) mas atribuído a actors diferentes
- [ ] **Testes unitários verdes:** todos os ~35–40 testes em `test_architectures.py` passando
- [ ] **Cenários e2e-quality passando** para as 3 arquiteturas com assertions específicas
- [ ] **Nenhuma regressão** nos testes existentes (22 testes atuais continuam verdes)
- [ ] **System prompts documentados** para cada agente de cada arquitetura

---

## 10. Fora de Escopo

Este plano foca exclusivamente na **diferenciação comportamental** das 3 arquiteturas. Os seguintes itens estão explicitamente fora de escopo:

- **Reescrever os domain tools** (`faq_lookup`, `stock_lookup`, `attachment_intake`) — permanecem como estão em `domain_tools.py`
- **Mudar a API pública** do `chat-api` — os endpoints `/messages`, `/conversations`, `/runs` não são alterados
- **Alterar o modo mock** — `_execute_mock` recebe ajustes mínimos de consistência (Passo 6), mas não é reescrito
- **Evaluator / LLM-as-judge** — a avaliação automática de qualidade das respostas é uma melhoria separada
- **Dashboard de comparação** — visualização lado-a-lado das métricas é trabalho futuro
- **WhatsApp adapter** — integração com canal WhatsApp não é afetada
- **Observabilidade OTEL** — tracing distribuído já está preparado mas não é expandido neste plano
