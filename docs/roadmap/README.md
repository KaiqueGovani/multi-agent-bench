# Roadmap — Multi-Agent Bench

> Plano de evolução da POC para o TCC de comparação de arquiteturas multi-agente.

---

## Visão Geral

O **Multi-Agent Bench** é uma POC de atendimento farmacêutico inteligente cujo objetivo acadêmico (TCC) é **comparar três arquiteturas de coordenação multi-agente**: Centralizada, Workflow Estruturado e Swarm Descentralizado.

**Estado atual (2026-05-01):**

- As três arquiteturas estão registradas, mas são **funcionalmente idênticas** em modo real.
- LLM real funciona via **Strands + Bedrock Claude Haiku 4.5** com tool use.
- Framework de qualidade E2E existe (`httpx` + `pytest` + cenários YAML em `tests/e2e-quality/`).
- Web UI com i18n PT-BR, abas por arquitetura e toggle mock/real.
- **Não há** relatório de benchmark, avaliação semântica nem dashboard comparativo.

Este roadmap organiza **5 melhorias** que transformam a POC em um ambiente experimental completo para o TCC.

---

## As 5 Melhorias

| # | Título | Descrição | Arquivo | Ordem | Tempo Est. | Dependências |
|---|--------|-----------|---------|:-----:|:----------:|:------------:|
| 01 | Architecture Differentiation | Tornar cada arquitetura comportamentalmente distinta (prompts, tools, fluxo) | [01-architecture-differentiation.md](./01-architecture-differentiation.md) | 1º | 2–3 dias | — |
| 02 | Architecture Benchmark | Executar cenários em lote e gerar relatório comparativo (latência, custo, acerto) | [02-architecture-benchmark.md](./02-architecture-benchmark.md) | 3º | 2–3 dias | 01, 03 |
| 03 | Scenario YAML Migration | Migrar e enriquecer cenários de teste para YAML com expectativas semânticas | [03-scenario-yaml-migration.md](./03-scenario-yaml-migration.md) | 2º | 1–2 dias | 01 |
| 04 | LLM-as-Judge | Avaliar respostas dos agentes com um LLM juiz (relevância, completude, tom) | [04-llm-as-judge.md](./04-llm-as-judge.md) | 3º–4º | 2–3 dias | 01, 03 |
| 05 | Architecture Comparison Dashboard | Painel web para visualizar métricas e comparar arquiteturas lado a lado | [05-architecture-comparison-dashboard.md](./05-architecture-comparison-dashboard.md) | 5º | 2–3 dias | 01, 02 |

---

## Ordem Recomendada de Execução

### 1º — Architecture Differentiation (01)

Fundação obrigatória. Sem diferenciação real, todas as medições posteriores comparam três cópias idênticas — o que invalida qualquer conclusão do TCC. Implementar prompts, tools e fluxos distintos para cada arquitetura.

### 2º — Scenario YAML Migration (03)

Com as arquiteturas diferenciadas, o próximo passo é criar cenários ricos em YAML que exercitem as diferenças. Esses cenários alimentam tanto o benchmark quanto o judge.

### 3º — Architecture Benchmark (02)

Agora os dados comparativos fazem sentido. Executar os cenários YAML contra as três arquiteturas, coletar métricas (latência, tokens, custo, acerto) e gerar relatórios.

### 4º — LLM-as-Judge (04) — *em paralelo com 02*

Pode rodar sobre os runs do benchmark para adicionar score semântico (relevância, completude, tom). Depende dos mesmos cenários YAML e da diferenciação, mas não bloqueia nem é bloqueado pelo benchmark.

### 5º — Comparison Dashboard (05)

Consumidor final de todos os dados. Só faz sentido quando há métricas reais (02) de arquiteturas realmente distintas (01) para visualizar.

---

## Dependências entre Melhorias

```
┌──────────────────────┐
│  01 Architecture     │
│  Differentiation     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  03 Scenario YAML    │
│  Migration           │
└──────────┬───────────┘
           │
     ┌─────┴──────┐
     │            │
     ▼            ▼
┌──────────┐  ┌──────────┐
│ 02 Bench │  │ 04 Judge │
│ mark     │  │ (LLM)    │
└────┬─────┘  └──────────┘
     │
     ▼
┌──────────────────────┐
│  05 Comparison       │
│  Dashboard           │◄── também depende de 01
└──────────────────────┘
```

**Resumo:** `01 → 03 → 02 → 05` | `01 + 03 → 04` | `01 + 02 → 05`

---

## Estado Atual dos Trabalhos

| # | Melhoria | Status |
|---|----------|--------|
| 01 | Architecture Differentiation | [ ] Não iniciado |
| 02 | Architecture Benchmark | [ ] Não iniciado |
| 03 | Scenario YAML Migration | [ ] Não iniciado |
| 04 | LLM-as-Judge | [ ] Não iniciado |
| 05 | Architecture Comparison Dashboard | [ ] Não iniciado |

> Atualize esta tabela conforme cada melhoria avançar: `[~]` Em progresso · `[x]` Concluído.

---

## Decisões Arquiteturais Atravessadas

Decisões que se aplicam a todas as melhorias:

| Aspecto | Decisão |
|---------|---------|
| **Source of truth dos cenários** | Arquivos YAML em `tests/e2e-quality/scenarios/` |
| **Linguagem da UI** | PT-BR |
| **Linguagem de código e logs** | Inglês |
| **LLM inference** | Amazon Bedrock via Strands SDK com tool use |
| **LLM judge** | Mesmo Bedrock via `langchain-aws` (custo unificado na mesma conta) |
| **Output do benchmark** | `var/reports/benchmark/<timestamp>/` (Markdown + JSON + CSV) |

---

## Como Contribuir

1. **Escolha uma melhoria** — abra o `.md` correspondente nesta pasta.
2. **Siga o plano** — cada documento contém seções *"Implementação Passo a Passo"* e *"Como Validar"*.
3. **Abra um PR** com commits seguindo [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   feat(runtime): differentiate centralized architecture prompt
   ```
4. **Se o plano precisar de ajuste** durante a implementação, edite o `.md` do plano no mesmo PR — mantemos os planos como documentos vivos.
5. Atualize a tabela de **Estado Atual** acima ao iniciar ou concluir uma melhoria.
