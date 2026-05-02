# 05 — Dashboard de Comparação de Arquiteturas

> Melhoria que adiciona a rota `/dashboard/compare` com visão side-by-side das 3 arquiteturas
> de coordenação multi-agente para o mesmo cenário, alimentada pelos runs do benchmark ou ad-hoc.

---

## Índice

1. [Contexto](#1-contexto)
2. [Estado Atual](#2-estado-atual)
3. [Estado Desejado](#3-estado-desejado)
4. [API — Endpoint de Comparação](#4-api--endpoint-de-comparação)
5. [Design Técnico Front-end](#5-design-técnico-front-end)
6. [Exemplo de UI (Wireframe)](#6-exemplo-de-ui-wireframe)
7. [Implementação Passo a Passo](#7-implementação-passo-a-passo)
8. [Como Validar](#8-como-validar)
9. [Riscos e Mitigações](#9-riscos-e-mitigações)
10. [Critérios de Pronto](#10-critérios-de-pronto)
11. [Fora de Escopo](#11-fora-de-escopo)

---

## 1. Contexto

O TCC compara três arquiteturas de coordenação multi-agente — **Orquestração Centralizada**,
**Workflow Estruturado** e **Swarm Descentralizado** — aplicadas ao atendimento farmacêutico.
Para a defesa, é essencial visualizar **"Arquitetura X vs Y vs Z no cenário A"** de forma
clara, com métricas agregadas, fluxo visual e amostra de execução lado a lado.

O dashboard atual (`/dashboard`) já possui bons building blocks — `MetricCard`,
`DistributionCard`, `CentralizedFlow`/`WorkflowFlow`/`SwarmFlow`, `RunExecutionPanel` — mas
**não monta essa view comparativa**. Cada componente opera isoladamente: métricas são globais,
o painel de execução mostra um único run por vez, e não há filtro por cenário.

Esta melhoria cria a página `/dashboard/compare` que reusa ao máximo os componentes existentes
e adiciona apenas o necessário para a comparação cross-arquitetura.

---

## 2. Estado Atual

### 2.1 Front-end

| Componente | Arquivo | Função |
|---|---|---|
| `DashboardWorkspace` | `dashboard-workspace.tsx` L:39 | Grid de `MetricCard` (5 KPIs), `ConversationRow`, `DistributionCard` ×4, `RunExecutionPanel` (single run) |
| `CentralizedFlow` | `architecture-flow.tsx` L:218 | ReactFlow: Supervisor → 3 especialistas → Streamer |
| `WorkflowFlow` | `architecture-flow.tsx` L:268 | ReactFlow: 5 estágios sequenciais |
| `SwarmFlow` | `architecture-flow.tsx` L:305 | ReactFlow: Coordenador → 3 especialistas → Sintetizador |
| `RunExecutionPanel` | `run-execution-panel.tsx` L:30 | Tabs (Visão Geral / Atividade / Técnico), replay, métricas |

### 2.2 Backend

| Recurso | Arquivo | Função |
|---|---|---|
| `GET /dashboard/metrics` | `routes/dashboard.py` L:11 | `DashboardMetricsResponse`: totals + distributions + latency percentiles |
| `DashboardService.get_metrics()` | `services/dashboard.py` L:18 | Carrega runs, calcula distribuições por `architectureKey`, `scenarioId` |
| `RunModel.experiment_json` | `db/models.py` L:119 | JSONB: `architectureKey`, `scenarioId`, `modelName`, etc. |
| `RunModel.summary_json` | `db/models.py` L:120 | JSONB: `inputTokens`, `outputTokens`, `toolCallCount`, `loopCount`, `estimatedCost` |
| `RunExecutionProjectionModel.metrics_json` | `db/models.py` L:163 | JSONB: `eventCount`, `toolCallCount`, `handoffCount`, `tokenUsage` |

### 2.3 Gaps Identificados

1. **Sem endpoint cross-arquitetura** — distribuições globais; sem agregação side-by-side por cenário.
2. **Sem filtro por cenário** — impossível pedir "métricas da arquitetura X apenas para cenário Y".
3. **Sem agregação de tokens/custo** — `_run_distribution()` (`dashboard.py` L:42) calcula apenas `count` + `avg_duration`.
4. **Sem time-series** — métricas são snapshots pontuais.
5. **`RunExecutionPanel` é single-run** — sem wrapper para 3 painéis lado a lado.
6. **`DistributionCard` limitado** — count + avg duration; sem multi-métrica.

---

## 3. Estado Desejado

Nova rota **`/dashboard/compare`** com:

### 3.1 Controles Globais

- **Seletor de cenário** — dropdown populado via `GET /dashboard/metrics` → `byScenario[].key`.
- **Seletor de período** — `últimas 24h` | `últimos 7 dias` | `todo o período`.

### 3.2 Layout em 3 Colunas

| Centralizada | Workflow | Swarm |
|---|---|---|
| `CentralizedFlow` | `WorkflowFlow` | `SwarmFlow` |
| 7 × `MetricCard` | 7 × `MetricCard` | 7 × `MetricCard` |
| `ComparisonBarChart` | `ComparisonBarChart` | `ComparisonBarChart` |
| 5 runs recentes | 5 runs recentes | 5 runs recentes |

Responsivo: 3 colunas em `xl`, stack vertical em mobile.

### 3.3 KPIs por Coluna (7 MetricCards)

| # | Label | Fonte | Ícone |
|---|---|---|---|
| 1 | Execuções | `runCount` | `Network` |
| 2 | Latência p50 | `p50` (ms) | `Timer` |
| 3 | Latência p95 | `p95` (ms) | `Clock3` |
| 4 | Tokens médios | `avgTokens` | `Database` |
| 5 | Tool calls médios | `avgToolCalls` | `Wrench` |
| 6 | Loop count médio | `avgLoopCount` | `Route` |
| 7 | Taxa de revisão | `reviewRate` (%) | `ShieldAlert` |

### 3.4 Gráfico Comparativo

`ComparisonBarChart` por coluna com dimensão selecionável (latência, tokens, tool calls) —
barras horizontais coloridas para as 3 arquiteturas.

### 3.5 Runs Recentes

Últimos 5 runs com link para `RunExecutionPanel` no `/dashboard` principal.

---

## 4. API — Endpoint de Comparação

### 4.1 Contrato

```
GET /dashboard/architecture-comparison?scenarioId={scenarioId}&since={ISO8601}
```

| Param | Tipo | Obrigatório | Default |
|---|---|---|---|
| `scenarioId` | `string` | não | `null` (todas) |
| `since` | `ISO8601 datetime` | não | `null` (all-time) |

### 4.2 Response Shape

```json
{
  "scenarioId": "dipirona_dor_de_cabeca",
  "since": "2026-04-24T00:00:00Z",
  "generatedAt": "2026-05-01T20:00:00Z",
  "architectures": {
    "centralized_orchestration": {
      "runCount": 12,
      "p50": 1200,
      "p95": 3100,
      "avgTokens": 450,
      "avgInputTokens": 280,
      "avgOutputTokens": 170,
      "avgToolCalls": 1.2,
      "avgLoopCount": 0.0,
      "reviewRate": 0.08,
      "avgEstimatedCost": 0.0032,
      "avgDurationMs": 1850,
      "recentRuns": [
        {
          "runId": "a1b2c3d4-...",
          "status": "completed",
          "totalDurationMs": 1400,
          "totalTokens": 520,
          "toolCallCount": 1,
          "createdAt": "2026-05-01T18:30:00Z"
        }
      ]
    },
    "structured_workflow": { "...mesmo shape..." },
    "decentralized_swarm": { "...mesmo shape..." }
  }
}
```

### 4.3 SQL de Agregação (PostgreSQL)

Novo método `get_architecture_comparison()` em `services/dashboard.py` (após L:156):

```sql
WITH filtered_runs AS (
  SELECT
    r.id,
    r.experiment_json->>'architectureKey'     AS arch_key,
    r.total_duration_ms,
    r.human_review_required,
    r.created_at,
    (r.summary_json->>'inputTokens')::int     AS input_tokens,
    (r.summary_json->>'outputTokens')::int    AS output_tokens,
    (r.summary_json->>'totalTokens')::int     AS total_tokens,
    (r.summary_json->>'toolCallCount')::int   AS tool_call_count,
    (r.summary_json->>'loopCount')::int       AS loop_count,
    (r.summary_json->>'estimatedCost')::float AS estimated_cost
  FROM runs r
  WHERE r.status IN ('completed', 'failed', 'human_review_required')
    AND (:scenario_id IS NULL OR r.experiment_json->>'scenarioId' = :scenario_id)
    AND (:since IS NULL OR r.created_at >= :since)
),
aggregated AS (
  SELECT
    arch_key,
    COUNT(*)                                                              AS run_count,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY total_duration_ms)       AS p50,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_duration_ms)       AS p95,
    ROUND(AVG(total_tokens))                                              AS avg_tokens,
    ROUND(AVG(input_tokens))                                              AS avg_input_tokens,
    ROUND(AVG(output_tokens))                                             AS avg_output_tokens,
    ROUND(AVG(tool_call_count)::numeric, 1)                               AS avg_tool_calls,
    ROUND(AVG(loop_count)::numeric, 1)                                    AS avg_loop_count,
    ROUND(AVG(CASE WHEN human_review_required THEN 1.0 ELSE 0.0 END)::numeric, 2)
                                                                          AS review_rate,
    ROUND(AVG(estimated_cost)::numeric, 4)                                AS avg_estimated_cost,
    ROUND(AVG(total_duration_ms))                                         AS avg_duration_ms
  FROM filtered_runs
  GROUP BY arch_key
)
SELECT * FROM aggregated;
```

Query para `recentRuns` (top 5 por arquitetura, usar `ROW_NUMBER()` no Python ou `LATERAL`):

```sql
SELECT r.id AS run_id, r.status, r.total_duration_ms,
       (r.summary_json->>'totalTokens')::int AS total_tokens,
       (r.summary_json->>'toolCallCount')::int AS tool_call_count,
       r.created_at, r.experiment_json->>'architectureKey' AS arch_key
FROM runs r
WHERE r.status IN ('completed', 'failed', 'human_review_required')
  AND (:scenario_id IS NULL OR r.experiment_json->>'scenarioId' = :scenario_id)
  AND (:since IS NULL OR r.created_at >= :since)
ORDER BY arch_key, r.created_at DESC
LIMIT 15;
```

> Implementar via `self._db.execute(text(...), params)` no SQLAlchemy.

### 4.4 Índice Recomendado

```sql
CREATE INDEX ix_runs_experiment_arch_scenario
  ON runs USING GIN (experiment_json jsonb_path_ops);

-- Alternativa B-tree:
CREATE INDEX ix_runs_arch_key ON runs ((experiment_json->>'architectureKey'));
CREATE INDEX ix_runs_scenario_id ON runs ((experiment_json->>'scenarioId'));
```

---

## 5. Design Técnico Front-end

### 5.1 Novos Arquivos

| Arquivo | Tipo |
|---|---|
| `apps/web/src/app/dashboard/compare/page.tsx` | Página Next.js |
| `apps/web/src/components/dashboard/architecture-comparison-view.tsx` | Componente principal |
| `apps/web/src/hooks/use-architecture-comparison.ts` | Hook de dados |

### 5.2 Tipos TypeScript

```typescript
// Adicionar em apps/web/src/lib/types.ts

export interface ArchitectureRunSummary {
  runId: string;
  status: string;
  totalDurationMs: number | null;
  totalTokens: number | null;
  toolCallCount: number | null;
  createdAt: string;
}

export interface ArchitectureMetrics {
  runCount: number;
  p50: number | null;
  p95: number | null;
  avgTokens: number | null;
  avgInputTokens: number | null;
  avgOutputTokens: number | null;
  avgToolCalls: number | null;
  avgLoopCount: number | null;
  reviewRate: number | null;
  avgEstimatedCost: number | null;
  avgDurationMs: number | null;
  recentRuns: ArchitectureRunSummary[];
}

export interface ArchitectureComparisonResponse {
  scenarioId: string | null;
  since: string | null;
  generatedAt: string;
  architectures: Record<ArchitectureMode, ArchitectureMetrics>;
}
```

### 5.3 Hook `useArchitectureComparison`

```typescript
// apps/web/src/hooks/use-architecture-comparison.ts
import { useEffect, useState } from "react";
import type { ArchitectureComparisonResponse } from "@/lib/types";

export function useArchitectureComparison(scenarioId: string | null, since: string | null) {
  const [data, setData] = useState<ArchitectureComparisonResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    const params = new URLSearchParams();
    if (scenarioId) params.set("scenarioId", scenarioId);
    if (since) params.set("since", since);

    fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/dashboard/architecture-comparison?${params}`, {
      headers: { "X-API-Key": process.env.NEXT_PUBLIC_API_KEY ?? "" },
    })
      .then((res) => { if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.json(); })
      .then((json) => { if (!cancelled) setData(json); })
      .catch((err) => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setIsLoading(false); });

    return () => { cancelled = true; };
  }, [scenarioId, since]);

  return { data, isLoading, error };
}
```

### 5.4 Props dos Componentes

```typescript
// ArchitectureComparisonView
interface ArchitectureComparisonViewProps {
  scenarios: { key: string; count: number }[];
}

// ArchitectureColumn
interface ArchitectureColumnProps {
  architectureMode: ArchitectureMode;
  title: string;
  metrics: ArchitectureMetrics | null;
  allMetrics: Record<ArchitectureMode, ArchitectureMetrics> | null;
  chartDimension: "latency" | "tokens" | "toolCalls";
}

// ComparisonBarChart
interface ComparisonBarChartProps {
  values: { label: string; value: number; color: string }[];
  unit: string;
  highlightIndex?: number;
}
```

### 5.5 Integração com Componentes Existentes

| Componente | Reuso | Referência |
|---|---|---|
| `MetricCard` | 7 instâncias por coluna | `dashboard-workspace.tsx` L:199 |
| `CentralizedFlow` | Coluna centralizada, modo estático (events `[]`) | `architecture-flow.tsx` L:218 |
| `WorkflowFlow` | Coluna workflow, modo estático | `architecture-flow.tsx` L:268 |
| `SwarmFlow` | Coluna swarm, modo estático | `architecture-flow.tsx` L:305 |

Os flows renderizam em modo **estático** (sem `executionEvents`), mostrando a topologia.
Se o último run tiver projeção, actors/edges refletem o estado final.

---

## 6. Exemplo de UI (Wireframe)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  ◀ Dashboard   Comparação de Arquiteturas                   [gerado às HH:MM]│
│  Cenário: [▼ dipirona_dor_de_cabeca ]   Período: [▼ Últimos 7 dias ]        │
├──────────────────────┬──────────────────────┬────────────────────────────────┤
│ 🔵 Orq. Centralizada │ 🟢 Workflow Estrutur.│ 🟠 Swarm Descentralizado      │
│ ┌──────────────────┐ │ ┌──────────────────┐ │ ┌──────────────────┐           │
│ │ CentralizedFlow  │ │ │  WorkflowFlow    │ │ │   SwarmFlow      │           │
│ └──────────────────┘ │ └──────────────────┘ │ └──────────────────┘           │
│ [12 runs][1.2s p50]  │ [10 runs][2.4s p50]  │ [ 8 runs][1.8s p50]           │
│ [3.1s p95][450 tkns] │ [5.2s p95][780 tkns] │ [4.5s p95][620 tkns]          │
│ [1.2 tool][0 loop]   │ [3.1 tool][0 loop]   │ [2.4 tool][1.5 loop]          │
│ [8% revisão]         │ [10% revisão]        │ [12% revisão]                 │
│                      │                      │                               │
│ ── Comparativo ───── │ ── Comparativo ───── │ ── Comparativo ─────          │
│ Dim: [▼ Latência p50]│                      │                               │
│ Centr ████████░░░░░  │ Centr ████████░░░░░  │ Centr ████████░░░░░           │
│ Workf ████████████░  │ Workf ████████████░  │ Workf ████████████░           │
│ Swarm ██████████░░░  │ Swarm ██████████░░░  │ Swarm ██████████░░░           │
│                      │                      │                               │
│ ── Runs recentes ──  │ ── Runs recentes ──  │ ── Runs recentes ──           │
│ a1b2c3d4 completed   │ e5f6g7h8 completed   │ i9j0k1l2 completed           │
│ m3n4o5p6 failed      │ q7r8s9t0 completed   │ u1v2w3x4 completed           │
└──────────────────────┴──────────────────────┴────────────────────────────────┘
```

Layout das MetricCards por coluna:

```
Linha 1:  [Execuções]  [p50 Latência]  [p95 Latência]
Linha 2:  [Tokens Médios]  [Tool Calls]  [Loop Count]
Linha 3:  [Taxa de Revisão]
```

---

## 7. Implementação Passo a Passo

### 7a. Backend — Endpoint + Service + SQL

1. **Novos schemas** em `apps/api/app/schemas/api.py` (após L:118):
   - `ArchitectureRunSummary`, `ArchitectureMetrics`, `ArchitectureComparisonResponse`

2. **Novo método** `get_architecture_comparison(scenario_id, since)` em `services/dashboard.py` (após L:156):
   - Query SQL da seção 4.3 via `self._db.execute(text(...))`
   - Dict `architectures` com 3 chaves fixas; chaves sem dados → zeros + `recentRuns: []`

3. **Novo endpoint** em `routes/dashboard.py` (após L:16):

   ```python
   @router.get("/dashboard/architecture-comparison", response_model=ArchitectureComparisonResponse)
   def get_architecture_comparison(
       scenario_id: str | None = Query(None, alias="scenarioId"),
       since: datetime | None = Query(None),
       db: Session = Depends(get_db_session),
   ) -> ArchitectureComparisonResponse:
       return DashboardService(db).get_architecture_comparison(scenario_id, since)
   ```

4. **Migração Alembic** para índice GIN (seção 4.4).

### 7b. Backend — Unit Test

Criar `apps/api/tests/services/test_dashboard_comparison.py`:
- Fixture: 9 runs (3 por arquitetura) para cenário `dipirona_dor_de_cabeca` + 3 de outro cenário
- Assertions: `runCount`, `p50`, `avgTokens`, `reviewRate`, `len(recentRuns)`

### 7c. Frontend — Hook + Componentes

1. Hook `use-architecture-comparison.ts` (seção 5.3)
2. `architecture-comparison-view.tsx` com `ArchitectureComparisonView`, `ArchitectureColumn`, `ComparisonBarChart`
3. Página `apps/web/src/app/dashboard/compare/page.tsx`:

   ```typescript
   import { Suspense } from "react";
   import { ArchitectureComparisonView } from "@/components/dashboard/architecture-comparison-view";

   export default function ComparePage() {
     return <Suspense><ArchitectureComparisonView scenarios={[]} /></Suspense>;
   }
   ```

### 7d. Frontend — Navegação

Adicionar no header de `DashboardWorkspace` (`dashboard-workspace.tsx` L:137):

```tsx
<Link className={cn(buttonVariants({ variant: "outline", size: "sm" }))} href="/dashboard/compare">
  <BarChart3 className="h-4 w-4" />
  Comparar arquiteturas
</Link>
```

### 7e. i18n

Labels em PT-BR (padrão do projeto). Reusar `formatArchitecture()` de `run-execution-panel.tsx` L:330:

| `architectureKey` | Label PT-BR |
|---|---|
| `centralized_orchestration` | Orquestração Centralizada |
| `structured_workflow` | Workflow Estruturado |
| `decentralized_swarm` | Swarm Descentralizado |

---

## 8. Como Validar

### 8.1 Popular o Banco

```bash
make benchmark --live                    # 3+ iterações → runs das 3 arquiteturas
# Ou cenário individual:
python scripts/run_fixture_scenarios.py --scenario dipirona_dor_de_cabeca --architecture all
```

### 8.2 Validação Manual

1. Abrir `http://localhost:3000/dashboard/compare`
2. Selecionar cenário no dropdown → 3 colunas populadas
3. Alternar dimensão do gráfico (latência → tokens → tool calls)
4. Clicar run recente → navega para `/dashboard?conversationId=...`
5. Redimensionar para mobile → colunas empilham verticalmente

### 8.3 Teste E2E (Playwright)

Criar `apps/web/tests/e2e/architecture-comparison.spec.ts`:
- `beforeEach`: mock de `**/dashboard/architecture-comparison**` com fixture das 3 arquiteturas
- Test: navegar para `/dashboard/compare?scenarioId=dipirona_dor_de_cabeca`
- Assertions: 3 títulos visíveis ("Orquestração Centralizada", "Workflow Estruturado", "Swarm Descentralizado"), KPIs corretos (`12` runs, `1.2 s` p50)

### 8.4 Acessibilidade

Rodar axe-core via Playwright — sem violations (contraste, labels, roles ARIA).

---

## 9. Riscos e Mitigações

| # | Risco | Mitigação |
|---|---|---|
| 1 | Endpoint vazio (sem runs para alguma arquitetura) | Empty-state por coluna + CTA "Rodar benchmark" |
| 2 | Query SQL lenta com muitos runs | Índice GIN (seção 4.4); cache TTL 60s; `recentRuns` limit 5 |
| 3 | Charts Tailwind com qualidade visual insuficiente | Usar **Recharts** `BarChart` se necessário; instalar com versão pinada |
| 4 | Flows estáticos parecem "mortos" | Edges em `idle`; se houver último run com projeção, usar estado final |
| 5 | Cenários com nomes longos quebram dropdown | `truncate` Tailwind + tooltip |
| 6 | `summary_json` vazio em runs antigos | Filtrar `total_tokens IS NOT NULL`; fallback "n/a" no front |

---

## 10. Critérios de Pronto

- [ ] `/dashboard/compare` funciona em dev local
- [ ] 3 arquiteturas populadas quando há runs no banco
- [ ] Empty-state funcional quando não há runs para uma arquitetura
- [ ] Layout responsivo: 3 colunas `xl`, stack vertical mobile
- [ ] Labels em PT-BR
- [ ] Playwright test verde (`architecture-comparison.spec.ts`)
- [ ] Unit test backend com fixtures de 3 arquiteturas
- [ ] Índice GIN via migração Alembic
- [ ] Recharts (ou alternativa) instalada com versão pinada se necessário
- [ ] Link "Comparar arquiteturas" no header do `/dashboard`
- [ ] Sem violations axe-core
- [ ] PR merged

---

## 11. Fora de Escopo

- **Não** mexer nas arquiteturas de agentes (melhoria 01)
- **Não** construir exportação PDF
- **Não** implementar time-series plot (possível iteração 2)
- **Não** comparação side-by-side de traces — `RunExecutionPanel` continua single-run
- **Não** filtro por modelo (`modelName`) nesta iteração
- **Não** WebSocket para atualização em tempo real da comparação
