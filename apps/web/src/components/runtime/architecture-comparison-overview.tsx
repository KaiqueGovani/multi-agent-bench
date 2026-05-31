"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ChevronDown,
  Clock3,
  GitCompareArrows,
  Hash,
  ShieldAlert,
  Timer,
  Wrench,
} from "lucide-react";

import { ArchitectureBarComparison, ArchitectureRadarChart } from "@/components/common/charts";
import { MarkdownContent } from "@/components/common/markdown-content";
import { CentralizedFlow, SwarmFlow, WorkflowFlow } from "@/components/runtime/architecture-flow";
import {
  formatActorLabel,
  formatArchitectureLabel,
  formatPhaseLabel,
  formatStatusLabel,
} from "@/components/runtime/presentation";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useRunExecution } from "@/hooks/use-run-execution";
import type { ArchitectureMode, JsonObject, Run, RunExecutionEvent } from "@/lib/types";

interface ArchitectureComparisonOverviewProps {
  runs: Run[];
}

export function ArchitectureComparisonOverview({ runs }: ArchitectureComparisonOverviewProps) {
  const latestByArchitecture = useMemo(() => buildLatestByArchitecture(runs), [runs]);
  const [now, setNow] = useState(() => Date.now());

  const centralized = useRunExecution(latestByArchitecture.centralized_orchestration?.id ?? null);
  const workflow = useRunExecution(latestByArchitecture.structured_workflow?.id ?? null);
  const swarm = useRunExecution(latestByArchitecture.decentralized_swarm?.id ?? null);

  const comparisons = [
    {
      architectureMode: "centralized_orchestration" as const,
      execution: centralized,
      run: centralized.run ?? latestByArchitecture.centralized_orchestration,
    },
    {
      architectureMode: "structured_workflow" as const,
      execution: workflow,
      run: workflow.run ?? latestByArchitecture.structured_workflow,
    },
    {
      architectureMode: "decentralized_swarm" as const,
      execution: swarm,
      run: swarm.run ?? latestByArchitecture.decentralized_swarm,
    },
  ];

  const availableComparisons = comparisons.filter((item) => item.run);

  // Check if any run is still active (use hook data for freshest status)
  const hasActiveRun = useMemo(() => {
    return (
      isLiveRun(centralized.run) ||
      isLiveRun(workflow.run) ||
      isLiveRun(swarm.run)
    );
  }, [centralized.run?.status, workflow.run?.status, swarm.run?.status]);

  useEffect(() => {
    if (!hasActiveRun) {
      return;
    }
    const timer = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(timer);
  }, [hasActiveRun]);

  if (availableComparisons.length === 0) {
    return (
      <Card className="shadow-none">
        <CardContent className="p-6 text-sm text-muted-foreground">
          Nenhuma execução comparável disponível ainda.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden shadow-none">
      <CardHeader className="border-b bg-card/60 p-4 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <GitCompareArrows className="h-4 w-4 text-primary" />
          <CardTitle>Comparação das arquiteturas</CardTitle>
        </div>
        <p className="text-sm text-muted-foreground">
          Acompanhe execução, uso de ferramentas e resposta final lado a lado.
        </p>
      </CardHeader>
      <CardContent className="p-4">
        <div className="grid gap-4 xl:grid-cols-3">
          {comparisons.map((item) => (
            <ArchitectureRunColumn
              activeActorName={
                item.execution.projection?.activeActorName
                ?? item.execution.activeEvent?.actorName
                ?? "runtime"
              }
              architectureMode={item.architectureMode}
              currentPhase={item.execution.projection?.currentPhase ?? null}
              executionEvents={item.execution.executionEvents}
              key={item.architectureMode}
              now={now}
              projection={item.execution.projection ?? null}
              run={item.run}
            />
          ))}
        </div>

        <ComparisonChartsSection comparisons={availableComparisons} />
      </CardContent>
    </Card>
  );
}

function ComparisonChartsSection({
  comparisons,
}: {
  comparisons: { architectureMode: string; execution: ReturnType<typeof useRunExecution>; run: Run | null }[];
}) {
  const { radarData, barData } = useMemo(() => {
    const getRunMetrics = (item: typeof comparisons[0]) => {
      const proj = item.execution.projection;
      const run = item.run;
      const metrics = proj?.metrics as Record<string, unknown> | undefined;
      const summary = run?.summary as Record<string, unknown> | undefined;
      return {
        duration: typeof run?.totalDurationMs === "number" ? run.totalDurationMs : 0,
        events: typeof metrics?.eventCount === "number" ? metrics.eventCount : item.execution.executionEvents.length,
        tools: typeof metrics?.toolCallCount === "number" ? metrics.toolCallCount
          : typeof summary?.toolCallCount === "number" ? summary.toolCallCount : 0,
        handoffs: typeof metrics?.handoffCount === "number" ? metrics.handoffCount : 0,
        inputTokens: typeof summary?.inputTokens === "number" ? summary.inputTokens
          : typeof (metrics?.tokenUsage as Record<string, unknown> | undefined)?.inputTokens === "number"
            ? (metrics!.tokenUsage as Record<string, number>).inputTokens : 0,
        outputTokens: typeof summary?.outputTokens === "number" ? summary.outputTokens
          : typeof (metrics?.tokenUsage as Record<string, unknown> | undefined)?.outputTokens === "number"
            ? (metrics!.tokenUsage as Record<string, number>).outputTokens : 0,
        totalTokens: typeof summary?.totalTokens === "number" ? summary.totalTokens
          : typeof (metrics?.tokenUsage as Record<string, unknown> | undefined)?.totalTokens === "number"
            ? (metrics!.tokenUsage as Record<string, number>).totalTokens : 0,
      };
    };

    const cent = comparisons.find((c) => c.architectureMode === "centralized_orchestration");
    const work = comparisons.find((c) => c.architectureMode === "structured_workflow");
    const swarm = comparisons.find((c) => c.architectureMode === "decentralized_swarm");

    const centM = cent ? getRunMetrics(cent) : { duration: 0, events: 0, tools: 0, handoffs: 0, inputTokens: 0, outputTokens: 0, totalTokens: 0 };
    const workM = work ? getRunMetrics(work) : { duration: 0, events: 0, tools: 0, handoffs: 0, inputTokens: 0, outputTokens: 0, totalTokens: 0 };
    const swarmM = swarm ? getRunMetrics(swarm) : { duration: 0, events: 0, tools: 0, handoffs: 0, inputTokens: 0, outputTokens: 0, totalTokens: 0 };

    const radar = [
      { metric: "Duração (s)", centralized: +(centM.duration / 1000).toFixed(1), workflow: +(workM.duration / 1000).toFixed(1), swarm: +(swarmM.duration / 1000).toFixed(1) },
      { metric: "Eventos", centralized: centM.events, workflow: workM.events, swarm: swarmM.events },
      { metric: "Ferramentas", centralized: centM.tools, workflow: workM.tools, swarm: swarmM.tools },
      { metric: "Handoffs", centralized: centM.handoffs, workflow: workM.handoffs, swarm: swarmM.handoffs },
    ];

    const bar = [
      { name: "Latência (s)", centralizada: +(centM.duration / 1000).toFixed(1), workflow: +(workM.duration / 1000).toFixed(1), swarm: +(swarmM.duration / 1000).toFixed(1) },
      { name: "Tokens totais", centralizada: centM.totalTokens, workflow: workM.totalTokens, swarm: swarmM.totalTokens },
      { name: "Tokens entrada", centralizada: centM.inputTokens, workflow: workM.inputTokens, swarm: swarmM.inputTokens },
      { name: "Tokens saída", centralizada: centM.outputTokens, workflow: workM.outputTokens, swarm: swarmM.outputTokens },
      { name: "Ferramentas", centralizada: centM.tools, workflow: workM.tools, swarm: swarmM.tools },
      { name: "Eventos", centralizada: centM.events, workflow: workM.events, swarm: swarmM.events },
    ];

    return { radarData: radar, barData: bar };
  }, [comparisons]);

  const hasData = radarData.some((d) => d.centralized > 0 || d.workflow > 0 || d.swarm > 0);
  if (!hasData) return null;

  const barDataWithValues = barData.filter((d) => d.centralizada > 0 || d.workflow > 0 || d.swarm > 0);
  const tokenBars = barDataWithValues.filter((d) => d.name.startsWith("Tokens"));
  const opsBars = barDataWithValues.filter((d) => !d.name.startsWith("Tokens"));

  const radarDataNormalized = radarData.map((row) => {
    const max = Math.max(row.centralized, row.workflow, row.swarm);
    const norm = (v: number) => (max > 0 ? Math.round((v / max) * 100) : 0);
    return {
      metric: row.metric,
      centralized: norm(row.centralized),
      workflow: norm(row.workflow),
      swarm: norm(row.swarm),
      centralizedRaw: row.centralized,
      workflowRaw: row.workflow,
      swarmRaw: row.swarm,
    };
  });

  return (
    <div className="mt-4 grid gap-4 lg:grid-cols-2">
      {tokenBars.length > 0 && (
        <div className="rounded-xl border bg-card/30 p-4">
          <ArchitectureBarComparison
            data={tokenBars}
            title="Tokens por arquitetura"
          />
        </div>
      )}
      {opsBars.length > 0 && (
        <div className="rounded-xl border bg-card/30 p-4">
          <ArchitectureBarComparison
            data={opsBars}
            title="Operação (latência · ferramentas · eventos)"
          />
        </div>
      )}
      <div className="rounded-xl border bg-card/30 p-4 lg:col-span-2">
        <p className="mb-2 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Radar comparativo
        </p>
        <ArchitectureRadarChart data={radarDataNormalized} />
      </div>
    </div>
  );
}

function ArchitectureRunColumn({
  activeActorName,
  architectureMode,
  currentPhase,
  executionEvents,
  now,
  projection,
  run,
}: {
  activeActorName: string;
  architectureMode: Exclude<ArchitectureMode, "all_architectures">;
  currentPhase: string | null;
  executionEvents: RunExecutionEvent[];
  now: number;
  projection: {
    architectureView: JsonObject;
    metrics: JsonObject;
    state?: JsonObject;
    activeActorName?: string | null;
  } | null;
  run: Run | null;
}) {
  const actors = useMemo(() => {
    const raw = projection?.architectureView?.actors;
    return raw && typeof raw === "object" ? Object.values(raw) : [];
  }, [projection?.architectureView]);

  const stages = useMemo(() => {
    const raw = projection?.architectureView?.stages;
    return Array.isArray(raw) ? raw : [];
  }, [projection?.architectureView]);

  const handoffs = useMemo(() => {
    const raw = projection?.architectureView?.handoffs;
    return Array.isArray(raw) ? raw : [];
  }, [projection?.architectureView]);

  const scenarioLabel = formatScenarioLabel(readExperimentString(run, "scenarioId"));
  const toolNames = listToolNames(executionEvents);
  const responsePreview = readResponsePreview(executionEvents);
  const metrics = projection?.metrics;
  const tokenUsage = readTokenUsage(run, metrics);

  return (
    <div className="grid gap-4 rounded-2xl border bg-background p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b pb-3">
        <div className="min-w-0 space-y-1">
          <p className="text-sm font-semibold tracking-tight">
            {formatArchitectureLabel(architectureMode)}
          </p>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>{run ? `run ${shortId(run.id)}` : "Sem run disponível"}</span>
            <span className="text-border">•</span>
            <span>{scenarioLabel}</span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {run ? (
            <Badge variant={statusVariant(run.status)}>{formatStatusLabel(run.status)}</Badge>
          ) : (
            <Badge variant="outline">sem dados</Badge>
          )}
          <Badge variant="outline">{formatRunDuration(run, now)}</Badge>
        </div>
      </div>

      <dl className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        <Metric icon={Activity} label="Status" value={formatStatusLabel(run?.status)} />
        <Metric icon={Clock3} label="Fase atual" value={formatPhaseLabel(currentPhase)} />
        <Metric icon={ShieldAlert} label="Revisão humana" value={run?.humanReviewRequired ? "Necessária" : "Não"} />
        <Metric icon={Timer} label="Tempo de execução" value={formatRunDuration(run, now)} />
        <Metric icon={Activity} label="Agente atual" value={formatActorLabel(activeActorName)} />
        <Metric icon={Hash} label="Tokens usados" value={formatTokenCount(tokenUsage.totalTokens)} />
        <Metric icon={Wrench} label="Ferramentas usadas" value={toolNames.length ? String(toolNames.length) : "0"} />
      </dl>

      <div className="grid gap-3 rounded-xl border bg-card/30 p-3">
        <SectionTitle title="Contexto" />
        <MetadataRow label="Cenário" value={scenarioLabel} />
        <MetadataRow
          label="Ferramentas usadas"
          value={toolNames.length ? toolNames.join(", ") : "Nenhuma"}
        />
        <MetadataRow
          label="Eventos"
          value={String(readMetricNumber(metrics, "eventCount", executionEvents.length))}
        />
        <MetadataRow
          label="Tokens"
          value={formatTokenBreakdown(tokenUsage)}
        />
      </div>

      <div className="grid gap-3">
        <SectionTitle title="Fluxo" />
        {projection ? (
          <RuntimeFlow
            activeActorName={activeActorName}
            architectureMode={architectureMode}
            actors={actors}
            executionEvents={executionEvents}
            handoffs={handoffs}
            runStatus={run?.status ?? readString(projection?.state, "lastStatus")}
            stages={stages}
          />
        ) : (
          <div className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
            Sem telemetria rica disponível para esta execução.
          </div>
        )}
      </div>

      <div className="grid gap-3 rounded-xl border bg-card/30 p-3">
        <SectionTitle title="Resposta" />
        {responsePreview ? (
          <CollapsibleMarkdownResponse content={responsePreview} />
        ) : (
          <p className="rounded-lg border border-dashed px-3 py-4 text-sm text-muted-foreground">
            A resposta final desta arquitetura ainda não foi recebida.
          </p>
        )}
      </div>
    </div>
  );
}

function CollapsibleMarkdownResponse({ content }: { content: string }) {
  return (
    <details
      className="group rounded-lg border bg-background/80 text-sm shadow-sm"
      data-testid="overview-response"
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 font-medium text-foreground transition-colors hover:bg-muted/50 [&::-webkit-details-marker]:hidden">
        <span>Mostrar resposta completa</span>
        <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" />
      </summary>
      <div className="border-t px-3 py-3">
        <MarkdownContent className="text-sm leading-6 text-foreground" content={content} />
      </div>
    </details>
  );
}

function RuntimeFlow({
  activeActorName,
  architectureMode,
  actors,
  executionEvents,
  handoffs,
  runStatus,
  stages,
}: {
  activeActorName: string;
  architectureMode: Exclude<ArchitectureMode, "all_architectures">;
  actors: unknown[];
  executionEvents: RunExecutionEvent[];
  handoffs: unknown[];
  runStatus: string | null;
  stages: unknown[];
}) {
  if (architectureMode === "structured_workflow") {
    return (
      <WorkflowFlow
        activeActorName={activeActorName}
        executionEvents={executionEvents}
        runStatus={runStatus}
        stages={stages}
      />
    );
  }

  if (architectureMode === "decentralized_swarm") {
    return (
      <SwarmFlow
        activeActorName={activeActorName}
        actors={actors}
        executionEvents={executionEvents}
        handoffs={handoffs}
        runStatus={runStatus}
      />
    );
  }

  return (
    <CentralizedFlow
      activeActorName={activeActorName}
      actors={actors}
      executionEvents={executionEvents}
      runStatus={runStatus}
    />
  );
}

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Activity;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border bg-card/50 px-3 py-3">
      <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-muted-foreground">
        <Icon className="h-3.5 w-3.5 shrink-0" />
        <dt className="truncate">{label}</dt>
      </div>
      <dd className="mt-1 truncate text-sm font-medium text-foreground">{value}</dd>
    </div>
  );
}

function MetadataRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1">
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="text-sm text-foreground">{value}</p>
    </div>
  );
}

function SectionTitle({ title }: { title: string }) {
  return <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">{title}</p>;
}

function buildLatestByArchitecture(runs: Run[]) {
  const map = new Map<string, Run>();
  const ordered = [...runs].sort((left, right) => {
    const timeDiff = new Date(left.createdAt).getTime() - new Date(right.createdAt).getTime();
    return timeDiff === 0 ? left.id.localeCompare(right.id) : timeDiff;
  });

  for (const run of ordered) {
    const architectureKey = readExperimentString(run, "architectureKey");
    if (!architectureKey || architectureKey === "all_architectures") {
      continue;
    }
    map.set(architectureKey, run);
  }

  return {
    centralized_orchestration: map.get("centralized_orchestration") ?? null,
    structured_workflow: map.get("structured_workflow") ?? null,
    decentralized_swarm: map.get("decentralized_swarm") ?? null,
  };
}

function listToolNames(executionEvents: RunExecutionEvent[]): string[] {
  const names = new Set<string>();
  for (const event of executionEvents) {
    const explicitTool = typeof event.toolName === "string" ? event.toolName : null;
    const payloadTool = typeof event.payload?.toolName === "string" ? event.payload.toolName : null;
    const value = explicitTool ?? payloadTool;
    if (value) {
      names.add(humanizeToken(value));
    }
  }
  return Array.from(names.values());
}

function readResponsePreview(executionEvents: RunExecutionEvent[]): string | null {
  const event = [...executionEvents]
    .reverse()
    .find((item) => item.eventFamily === "response" && item.eventName === "final");
  const contentText = event?.payload?.contentText;
  return typeof contentText === "string" && contentText.trim().length > 0
    ? contentText.trim()
    : null;
}

function readExperimentString(run: Run | null, key: string): string | null {
  const value = run?.experiment?.[key];
  return typeof value === "string" ? value : null;
}

function readMetricNumber(
  metrics: JsonObject | undefined,
  key: string,
  fallback = 0,
): number {
  const value = metrics?.[key];
  return typeof value === "number" ? value : fallback;
}

interface TokenUsage {
  inputTokens: number | null;
  outputTokens: number | null;
  totalTokens: number | null;
}

function readTokenUsage(run: Run | null, metrics: JsonObject | undefined): TokenUsage {
  const summaryUsage = readTokenUsageFromObject(run?.summary);
  if (summaryUsage.totalTokens !== null || summaryUsage.inputTokens !== null || summaryUsage.outputTokens !== null) {
    return summaryUsage;
  }

  const metricUsage = readTokenUsageFromObject(metrics?.tokenUsage);
  if (metricUsage.totalTokens !== null || metricUsage.inputTokens !== null || metricUsage.outputTokens !== null) {
    return metricUsage;
  }

  return {
    inputTokens: null,
    outputTokens: null,
    totalTokens: null,
  };
}

function readTokenUsageFromObject(value: unknown): TokenUsage {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {
      inputTokens: null,
      outputTokens: null,
      totalTokens: null,
    };
  }

  const object = value as Record<string, unknown>;
  const inputTokens = readNumberFromObject(object, [
    "inputTokens",
    "input_tokens",
    "promptTokens",
    "prompt_tokens",
  ]);
  const outputTokens = readNumberFromObject(object, [
    "outputTokens",
    "output_tokens",
    "completionTokens",
    "completion_tokens",
  ]);
  const totalTokens = readNumberFromObject(object, ["totalTokens", "total_tokens"])
    ?? (inputTokens !== null && outputTokens !== null ? inputTokens + outputTokens : null);

  return {
    inputTokens,
    outputTokens,
    totalTokens,
  };
}

function readNumberFromObject(object: Record<string, unknown>, keys: string[]): number | null {
  for (const key of keys) {
    const value = object[key];
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
  }
  return null;
}

function readString(object: JsonObject | undefined, key: string): string | null {
  const value = object?.[key];
  return typeof value === "string" ? value : null;
}

function statusVariant(status: string | null | undefined) {
  if (status === "completed") {
    return "success" as const;
  }
  if (status === "running") {
    return "warning" as const;
  }
  if (status === "failed" || status === "human_review_required") {
    return "destructive" as const;
  }
  if (status === "pending") {
    return "muted" as const;
  }
  return "outline" as const;
}

const SCENARIO_LABELS: Record<string, string> = {
  stock_inquiry: "Consulta de estoque",
  clinical_guidance: "Orientação clínica",
  faq_inquiry: "Dúvida frequente (FAQ)",
  general_inquiry: "Consulta geral",
  attachment_analysis: "Análise de anexo",
  unknown: "Não classificado",
};

function formatScenarioLabel(value: string | null): string {
  if (!value) {
    return "Comparação geral";
  }
  return SCENARIO_LABELS[value] ?? humanizeToken(value);
}

const TOOL_NAME_MAP: Record<string, string> = {
  handoff_to_peer: "Handoff entre pares",
  faq_lookup: "Consulta FAQ",
  stock_lookup: "Consulta de estoque",
  attachment_intake: "Análise de anexo",
  multi_modal: "Multimodal",
};

function humanizeToken(value: string): string {
  const lower = value.toLowerCase().replaceAll("-", "_");
  if (TOOL_NAME_MAP[lower]) {
    return TOOL_NAME_MAP[lower];
  }
  return value
    .replaceAll("-", " ")
    .replaceAll("_", " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatDuration(value: number | null | undefined): string {
  if (!value) {
    return "n/a";
  }
  if (value < 1000) {
    return `${value} ms`;
  }
  return `${(value / 1000).toFixed(1)} s`;
}

function formatTokenCount(value: number | null): string {
  if (value === null) {
    return "n/a";
  }
  return new Intl.NumberFormat("pt-BR").format(value);
}

function formatTokenBreakdown(usage: TokenUsage): string {
  const parts: string[] = [];
  if (usage.inputTokens !== null) {
    parts.push(`entrada ${formatTokenCount(usage.inputTokens)}`);
  }
  if (usage.outputTokens !== null) {
    parts.push(`saida ${formatTokenCount(usage.outputTokens)}`);
  }
  if (usage.totalTokens !== null) {
    parts.push(`total ${formatTokenCount(usage.totalTokens)}`);
  }
  return parts.length ? parts.join(" · ") : "Não informado";
}

function shortId(value: string): string {
  return value.slice(0, 8);
}

function isLiveRun(run: Run | null): boolean {
  if (!run) {
    return false;
  }
  return !["completed", "failed", "cancelled", "human_review_required"].includes(run.status);
}

function formatRunDuration(run: Run | null, now: number): string {
  if (!run) {
    return "n/a";
  }
  // Use totalDurationMs when run is completed
  if (typeof run.totalDurationMs === "number" && run.totalDurationMs > 0) {
    return formatDuration(run.totalDurationMs);
  }
  // For completed runs without duration, show "completed"
  if (["completed", "failed", "cancelled", "human_review_required"].includes(run.status)) {
    return "concluído";
  }
  const anchor = run.startedAt ?? run.createdAt ?? null;
  if (!anchor) {
    return "n/a";
  }
  const elapsed = now - new Date(anchor).getTime();
  return formatDuration(Math.max(elapsed, 0));
}
