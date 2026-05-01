"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Bot,
  Clock3,
  GitBranch,
  Network,
  Pause,
  Play,
  Route,
  ShieldAlert,
  Sparkles,
  Timer,
  Wrench,
  type LucideIcon,
} from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CentralizedFlow, SwarmFlow, WorkflowFlow } from "@/components/runtime/architecture-flow";
import { useRunExecution } from "@/hooks/use-run-execution";
import type {
  ArchitectureMode,
  JsonObject,
  Run,
  RunExecutionEvent,
} from "@/lib/types";

type PanelVariant = "user" | "technical";

interface RunExecutionPanelProps {
  runs: Run[];
  selectedRunId: string | null;
  onSelectRun: (runId: string) => void;
  variant?: PanelVariant;
  /** When true, hides the internal tab bar and renders only the overview content. */
  hideTabs?: boolean;
}

export function RunExecutionPanel({
  runs,
  selectedRunId,
  onSelectRun,
  variant = "user",
  hideTabs = false,
}: RunExecutionPanelProps) {
  const {
    activeEvent,
    comparisonContext,
    connectionStatus,
    error,
    executionEvents,
    projection,
    run,
  } = useRunExecution(selectedRunId);
  const [isReplayPlaying, setIsReplayPlaying] = useState(false);
  const [replayIndex, setReplayIndex] = useState(0);
  const [activeTab, setActiveTab] = useState<"overview" | "activity" | "technical">("overview");

  // When hideTabs is enabled, always show the overview content
  const effectiveTab = hideTabs ? "overview" : activeTab;

  useEffect(() => {
    setReplayIndex(Math.max(executionEvents.length - 1, 0));
  }, [executionEvents.length, selectedRunId]);

  useEffect(() => {
    if (!isReplayPlaying || executionEvents.length === 0) {
      return;
    }
    const timer = window.setInterval(() => {
      setReplayIndex((current) => {
        if (current >= executionEvents.length - 1) {
          setIsReplayPlaying(false);
          return current;
        }
        return current + 1;
      });
    }, 700);
    return () => window.clearInterval(timer);
  }, [executionEvents.length, isReplayPlaying]);

  const replayEvent =
    executionEvents[Math.min(replayIndex, Math.max(executionEvents.length - 1, 0))];
  const architectureMode = (projection?.architectureMode ??
    run?.experiment?.architectureKey ??
    "centralized_orchestration") as ArchitectureMode;
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

  const toolCallCount = readMetricNumber(projection?.metrics, "toolCallCount");
  const handoffCount = readMetricNumber(projection?.metrics, "handoffCount");
  const eventCount = readMetricNumber(projection?.metrics, "eventCount");
  const activeActorName =
    projection?.activeActorName ?? activeEvent?.actorName ?? "runtime";
  const currentPhase = projection?.currentPhase ?? "dispatch";
  const panelTitle =
    variant === "technical" ? "Monitor técnico do runtime" : "Acompanhamento da execução";
  const panelDescription =
    variant === "technical"
      ? "Superfície dedicada para inspeção operacional, replay e contexto comparativo."
      : "Fluxo visual do runtime para consulta opcional durante a conversa.";

  const tabs = useMemo(() => {
    const base: { key: "overview" | "activity" | "technical"; label: string }[] = [
      { key: "overview", label: "Visão Geral" },
      { key: "activity", label: "Atividade" },
    ];
    if (variant === "technical") {
      base.push({ key: "technical", label: "Técnico" });
    }
    return base;
  }, [variant]);

  return (
    <section
      className={variant === "technical" ? "grid gap-4" : "border-b bg-card/50"}
      data-testid={`runtime-panel-${variant}`}
    >
      <div
        className={
          variant === "technical"
            ? "grid gap-4"
            : "mx-auto grid max-h-[calc(100vh-10rem)] w-full max-w-7xl gap-3 overflow-y-auto overscroll-contain p-4"
        }
      >
        <motion.div
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between gap-3 rounded-2xl border bg-card/90 px-4 py-3 shadow-sm"
          initial={{ opacity: 0, y: 8 }}
          transition={{ duration: 0.24, ease: "easeOut" }}
        >
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <h2 className="text-sm font-semibold">{panelTitle}</h2>
              <Badge variant="outline">{formatArchitecture(architectureMode)}</Badge>
              <Badge variant={connectionStatus === "open" ? "success" : "warning"}>
                {connectionStatus}
              </Badge>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">{panelDescription}</p>
          </div>

          {variant === "user" ? (
            <Badge variant="outline" className="text-xs">modo usuário</Badge>
          ) : null}
        </motion.div>

        {/* Tab bar */}
        {!hideTabs ? (
        <div className="flex items-center gap-1 rounded-lg border bg-muted/40 p-1">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        ) : null}

        {/* Tab content panels */}
        <AnimatePresence mode="wait">
          {effectiveTab === "overview" ? (
            <motion.div
              animate={{ opacity: 1, y: 0 }}
              className="max-h-[calc(100vh-16rem)] overflow-y-auto overscroll-contain"
              exit={{ opacity: 0, y: -4 }}
              initial={{ opacity: 0, y: 4 }}
              key="tab-overview"
              transition={{ duration: 0.2, ease: "easeOut" }}
            >
              <Card className="overflow-hidden border-primary/15 bg-gradient-to-br from-card via-card to-primary/5 shadow-none">
                <CardContent className="grid gap-4 p-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Route className="h-4 w-4 text-primary" />
                        <h3 className="text-sm font-semibold">
                          {variant === "technical" ? "Mapa visual da execução" : "Resumo da execução"}
                        </h3>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {variant === "technical"
                          ? "O monitor técnico concentra replay, distribuição, nós e transições recentes em uma superfície operacional dedicada."
                          : "Resumo visual do runtime para acompanhar agentes, transferências e chamadas de ferramenta sem poluir o fluxo da conversa."}
                      </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <select
                        className="h-9 rounded-md border bg-background px-3 text-sm"
                        onChange={(event) => onSelectRun(event.target.value)}
                        value={selectedRunId ?? ""}
                      >
                        {runs.map((candidate) => (
                          <option key={candidate.id} value={candidate.id}>
                            execução {shortId(candidate.id)} - {candidate.status}
                          </option>
                        ))}
                      </select>
                      {variant === "technical" ? <Badge variant="outline">modo técnico</Badge> : null}
                    </div>
                  </div>

                  {error ? (
                    <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
                      {error}
                    </div>
                  ) : null}

                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <SummaryMetric icon={Route} label="Status" value={run?.status ?? "n/a"} />
                    <SummaryMetric icon={Bot} label="Agente atual" value={activeActorName} />
                    <SummaryMetric icon={Clock3} label="Fase" value={currentPhase} />
                    <SummaryMetric icon={Timer} label="Latência" value={formatDuration(run?.totalDurationMs)} />
                  </div>

                  <Card className="border-primary/10 bg-background/80 shadow-none">
                    <CardHeader className="p-4 pb-2">
                      <CardTitle>Fluxo visual</CardTitle>
                    </CardHeader>
                    <CardContent className="p-4 pt-0">
                      <RuntimeVisual
                        activeActorName={activeActorName}
                        architectureMode={architectureMode}
                        actors={actors}
                        executionEvents={executionEvents}
                        handoffs={handoffs}
                        stages={stages}
                      />
                    </CardContent>
                  </Card>

                  <Card className="border-primary/10 bg-background/80 shadow-none">
                    <CardHeader className="p-4 pb-2">
                      <CardTitle>Indicadores</CardTitle>
                    </CardHeader>
                    <CardContent className="grid gap-2 p-4 pt-0">
                      <InfoRow icon={Wrench} label="chamadas de ferramenta" value={String(toolCallCount)} />
                      <InfoRow icon={Network} label="transferências" value={String(handoffCount)} />
                      <InfoRow icon={Activity} label="eventos" value={String(eventCount)} />
                      <InfoRow
                        icon={ShieldAlert}
                        label="revisão"
                        value={run?.humanReviewRequired ? "necessária" : "livre"}
                      />
                    </CardContent>
                  </Card>
                </CardContent>
              </Card>
            </motion.div>
          ) : null}

          {effectiveTab === "activity" ? (
            <motion.div
              animate={{ opacity: 1, y: 0 }}
              className="max-h-[calc(100vh-16rem)] overflow-y-auto overscroll-contain"
              exit={{ opacity: 0, y: -4 }}
              initial={{ opacity: 0, y: 4 }}
              key="tab-activity"
              transition={{ duration: 0.2, ease: "easeOut" }}
            >
              <Card className="border-primary/15 shadow-none">
                <CardHeader className="p-4 pb-2">
                  <CardTitle>{variant === "technical" ? "Atividade de runtime" : "Atividade recente"}</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-2 p-4 pt-0">
                  {executionEvents.length === 0 ? (
                    <p className="text-xs text-muted-foreground">
                      Nenhum evento rico registrado ainda.
                    </p>
                  ) : (
                    executionEvents
                      .slice()
                      .reverse()
                      .map((event) => (
                        <motion.div
                          animate={{ opacity: 1, x: 0 }}
                          className="flex items-center gap-2 rounded-md border bg-muted/20 px-3 py-2 text-xs"
                          initial={{ opacity: 0, x: 8 }}
                          key={event.id}
                          transition={{ duration: 0.2, ease: "easeOut" }}
                        >
                          <EventBadge event={event} />
                          <span className="min-w-0 truncate font-medium">
                            {event.actorName ?? "runtime"}
                          </span>
                          <span className="ml-auto text-muted-foreground">
                            {event.eventFamily}.{event.eventName}
                          </span>
                        </motion.div>
                      ))
                  )}
                </CardContent>
              </Card>
            </motion.div>
          ) : null}

          {effectiveTab === "technical" && variant === "technical" ? (
            <motion.div
              animate={{ opacity: 1, y: 0 }}
              className="max-h-[calc(100vh-16rem)] overflow-y-auto overscroll-contain"
              exit={{ opacity: 0, y: -4 }}
              initial={{ opacity: 0, y: 4 }}
              key="tab-technical"
              transition={{ duration: 0.2, ease: "easeOut" }}
            >
              <div className="grid gap-3 xl:grid-cols-[1.1fr_1.2fr_1fr]">
                <Card className="shadow-none">
                  <CardHeader className="p-3 pb-1">
                    <CardTitle>Replay técnico</CardTitle>
                  </CardHeader>
                  <CardContent className="grid gap-3 p-3 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <Button
                        disabled={executionEvents.length === 0}
                        onClick={() => setIsReplayPlaying((current) => !current)}
                        size="sm"
                        type="button"
                        variant="outline"
                      >
                        {isReplayPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                        Replay
                      </Button>
                      <Badge variant="outline">
                        {replayEvent ? `${replayIndex + 1}/${executionEvents.length}` : "0/0"}
                      </Badge>
                    </div>
                    <div className="rounded-md border bg-background p-3">
                      {replayEvent ? (
                        <>
                          <p className="font-medium text-foreground">
                            {replayEvent.eventFamily}.{replayEvent.eventName}
                          </p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {replayEvent.actorName ?? "runtime"} · {replayEvent.status}
                          </p>
                          <p className="mt-3 text-xs text-muted-foreground">
                            seq {replayEvent.sequenceNo} · {replayEvent.nodeId ?? "no-node"}
                          </p>
                        </>
                      ) : (
                        <p className="text-xs text-muted-foreground">
                          Nenhum evento rico registrado ainda.
                        </p>
                      )}
                    </div>
                    <InfoRow icon={GitBranch} label="rastreio" value={run?.traceId ?? "n/a"} />
                  </CardContent>
                </Card>

                <Card className="shadow-none">
                  <CardHeader className="p-3 pb-1">
                    <CardTitle>Eventos técnicos</CardTitle>
                  </CardHeader>
                  <CardContent className="grid gap-2 p-3 text-xs">
                    {executionEvents.length === 0 ? (
                      <p className="text-muted-foreground">
                        Aguardando execução rica do runtime.
                      </p>
                    ) : (
                      executionEvents
                        .slice(-8)
                        .reverse()
                        .map((event) => (
                          <div className="rounded-md border bg-background p-3" key={event.id}>
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-medium">
                                {event.eventFamily}.{event.eventName}
                              </span>
                              <Badge variant={statusBadgeVariant(event.status)}>
                                {event.status}
                              </Badge>
                            </div>
                            <p className="mt-1 text-muted-foreground">
                              {event.actorName ?? "runtime"} · seq {event.sequenceNo}
                            </p>
                            {event.toolName ? (
                              <p className="mt-1 text-muted-foreground">tool {event.toolName}</p>
                            ) : null}
                          </div>
                        ))
                    )}
                  </CardContent>
                </Card>

                <Card className="shadow-none">
                  <CardHeader className="p-3 pb-1">
                    <CardTitle>Comparação e contexto</CardTitle>
                  </CardHeader>
                  <CardContent className="grid gap-3 p-3 text-xs">
                    <div className="grid gap-2">
                      {(comparisonContext?.architectureDistribution ?? []).map((entry) => (
                        <div className="rounded-md border bg-background p-3" key={entry.key}>
                          <p className="font-medium">{entry.key}</p>
                          <p className="mt-1 text-muted-foreground">
                            {entry.count} execuções · média {formatDuration(entry.averageRunDurationMs)}
                          </p>
                        </div>
                      ))}
                    </div>
                    <div className="rounded-md border bg-background p-3">
                      <p className="font-medium">Execuções relacionadas</p>
                      <p className="mt-1 text-muted-foreground">
                        {(comparisonContext?.peerRuns ?? []).length} execuções relacionadas ao mesmo cenário ou arquitetura.
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </section>
  );
}

function RuntimeVisual({
  activeActorName,
  architectureMode,
  actors,
  executionEvents,
  handoffs,
  stages,
}: {
  activeActorName: string;
  architectureMode: ArchitectureMode;
  actors: unknown[];
  executionEvents: RunExecutionEvent[];
  handoffs: unknown[];
  stages: unknown[];
}) {
  if (architectureMode === "structured_workflow") {
    return (
      <WorkflowFlow
        activeActorName={activeActorName}
        stages={stages}
        executionEvents={executionEvents}
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
      />
    );
  }

  return (
    <CentralizedFlow
      activeActorName={activeActorName}
      actors={actors}
      executionEvents={executionEvents}
    />
  );
}

function SummaryMetric({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <motion.div
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-primary/10 bg-background/80 p-3 shadow-sm"
      initial={{ opacity: 0, y: 10 }}
      transition={{ duration: 0.22, ease: "easeOut" }}
    >
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-primary/10 p-2 text-primary">
          <Icon className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{value}</p>
          <p className="text-[11px] text-muted-foreground">{label}</p>
        </div>
      </div>
    </motion.div>
  );
}

function InfoRow({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-2 rounded-md border bg-background px-3 py-2">
      <Icon className="h-3.5 w-3.5 text-primary" />
      <span className="text-muted-foreground">{label}</span>
      <span className="ml-auto truncate font-medium text-foreground">{value}</span>
    </div>
  );
}

function EventBadge({ event }: { event: RunExecutionEvent }) {
  if (event.eventFamily === "tool") {
    return <Badge variant="info">ferramenta</Badge>;
  }
  if (event.eventFamily === "handoff") {
    return <Badge variant="warning">transferência</Badge>;
  }
  if (event.eventFamily === "review") {
    return <Badge variant="destructive">revisão</Badge>;
  }
  if (event.eventFamily === "response") {
    return <Badge variant="success">resposta</Badge>;
  }
  return <Badge variant="muted">{event.eventFamily}</Badge>;
}

function readMetricNumber(metrics: JsonObject | undefined, key: string): number {
  const value = metrics?.[key];
  return typeof value === "number" ? value : 0;
}

function statusBadgeVariant(status: string): BadgeProps["variant"] {
  if (status === "completed") {
    return "success";
  }
  if (status === "running") {
    return "warning";
  }
  if (status === "failed" || status === "human_review_required") {
    return "destructive";
  }
  if (status === "pending") {
    return "muted";
  }
  return "outline";
}

function formatArchitecture(mode: ArchitectureMode): string {
  if (mode === "structured_workflow") {
    return "Workflow Estruturado";
  }
  if (mode === "decentralized_swarm") {
    return "Swarm Descentralizado";
  }
  return "Orquestração Centralizada";
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

function shortId(value: string): string {
  return value.slice(0, 8);
}
