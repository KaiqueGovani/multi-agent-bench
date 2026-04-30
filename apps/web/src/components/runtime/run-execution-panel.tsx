"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  Bot,
  ChevronDown,
  ChevronUp,
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
} from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useRunExecution } from "@/hooks/use-run-execution";
import type {
  ArchitectureMode,
  JsonObject,
  Run,
  RunExecutionEvent,
} from "@/lib/types";

interface RunExecutionPanelProps {
  runs: Run[];
  selectedRunId: string | null;
  onSelectRun: (runId: string) => void;
}

interface FlowNodeData {
  actorName: string;
  status: string;
  nodeId?: string | null;
  tone?: BadgeProps["variant"];
  active?: boolean;
}

export function RunExecutionPanel({
  runs,
  selectedRunId,
  onSelectRun,
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
  const [isOverviewOpen, setIsOverviewOpen] = useState(false);
  const [isTechnicalOpen, setIsTechnicalOpen] = useState(false);

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

  return (
    <section className="border-b bg-card/50">
      <div className="mx-auto grid w-full max-w-7xl gap-3 p-4">
        <div className="flex items-center justify-between gap-3 rounded-xl border bg-card/80 px-4 py-3 shadow-sm">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <h2 className="text-sm font-semibold">Acompanhamento da execução</h2>
              <Badge variant="outline">{formatArchitecture(architectureMode)}</Badge>
              <Badge variant={connectionStatus === "open" ? "success" : "warning"}>
                {connectionStatus}
              </Badge>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Fluxo visual do runtime para consulta opcional durante a conversa.
            </p>
          </div>
          <Button
            onClick={() => setIsOverviewOpen((current) => !current)}
            size="sm"
            type="button"
            variant={isOverviewOpen ? "default" : "outline"}
          >
            {isOverviewOpen ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
            {isOverviewOpen ? "Ocultar acompanhamento" : "Ver acompanhamento"}
          </Button>
        </div>

        {isOverviewOpen ? (
          <Card className="max-h-[46vh] overflow-hidden border-primary/15 bg-gradient-to-br from-card via-card to-primary/5 shadow-none">
            <div className="max-h-[46vh] overflow-y-auto">
              <CardContent className="grid gap-4 p-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Route className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-semibold">Resumo da run</h3>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Resumo visual do runtime para acompanhar agentes, handoffs e tool calls sem poluir o fluxo da conversa.
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
                      run {shortId(candidate.id)} - {candidate.status}
                    </option>
                  ))}
                </select>
                <Button
                  onClick={() => setIsTechnicalOpen((current) => !current)}
                  size="sm"
                  type="button"
                  variant={isTechnicalOpen ? "default" : "outline"}
                >
                  {isTechnicalOpen ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                  {isTechnicalOpen ? "Ocultar execução técnica" : "Ver execução técnica"}
                </Button>
              </div>
            </div>

            {error ? (
              <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            ) : null}

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <SummaryMetric
                icon={Route}
                label="Status"
                value={run?.status ?? "n/a"}
              />
              <SummaryMetric
                icon={Bot}
                label="Agente atual"
                value={activeActorName}
              />
              <SummaryMetric
                icon={Clock3}
                label="Fase"
                value={currentPhase}
              />
              <SummaryMetric
                icon={Timer}
                label="Latencia"
                value={formatDuration(run?.totalDurationMs)}
              />
            </div>

            <div className="grid gap-3 xl:grid-cols-[1.7fr_1fr]">
              <Card className="border-primary/10 bg-background/80 shadow-none">
                <CardHeader className="p-4 pb-2">
                  <CardTitle>Fluxo visual</CardTitle>
                </CardHeader>
                <CardContent className="p-4 pt-0">
                  <RuntimeVisual
                    activeActorName={activeActorName}
                    architectureMode={architectureMode}
                    actors={actors}
                    handoffs={handoffs}
                    stages={stages}
                  />
                </CardContent>
              </Card>

              <div className="grid gap-3">
                <Card className="border-primary/10 bg-background/80 shadow-none">
                  <CardHeader className="p-4 pb-2">
                    <CardTitle>Indicadores</CardTitle>
                  </CardHeader>
                  <CardContent className="grid gap-2 p-4 pt-0">
                    <InfoRow icon={Wrench} label="tool calls" value={String(toolCallCount)} />
                    <InfoRow icon={Network} label="handoffs" value={String(handoffCount)} />
                    <InfoRow icon={Activity} label="eventos" value={String(eventCount)} />
                    <InfoRow
                      icon={ShieldAlert}
                      label="review"
                      value={run?.humanReviewRequired ? "required" : "clear"}
                    />
                  </CardContent>
                </Card>

                <Card className="border-primary/10 bg-background/80 shadow-none">
                  <CardHeader className="p-4 pb-2">
                    <CardTitle>Atividade recente</CardTitle>
                  </CardHeader>
                  <CardContent className="grid gap-2 p-4 pt-0">
                    {executionEvents.length === 0 ? (
                      <p className="text-xs text-muted-foreground">
                        Nenhum evento rico registrado ainda.
                      </p>
                    ) : (
                      executionEvents
                        .slice(-4)
                        .reverse()
                        .map((event) => (
                          <div
                            className="flex items-center gap-2 rounded-md border bg-muted/20 px-3 py-2 text-xs"
                            key={event.id}
                          >
                            <EventBadge event={event} />
                            <span className="min-w-0 truncate font-medium">
                              {event.actorName ?? "runtime"}
                            </span>
                            <span className="ml-auto text-muted-foreground">
                              {event.eventFamily}.{event.eventName}
                            </span>
                          </div>
                        ))
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
              </CardContent>
            </div>
          </Card>
        ) : null}

        {isOverviewOpen && isTechnicalOpen ? (
          <div className="grid gap-3 xl:grid-cols-[1.1fr_1.2fr_1fr]">
            <Card className="shadow-none">
              <CardHeader className="p-3 pb-1">
                <CardTitle>Replay tecnico</CardTitle>
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
                    {isReplayPlaying ? (
                      <Pause className="h-4 w-4" />
                    ) : (
                      <Play className="h-4 w-4" />
                    )}
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
                        {replayEvent.actorName ?? "runtime"} - {replayEvent.status}
                      </p>
                      <p className="mt-3 text-xs text-muted-foreground">
                        seq {replayEvent.sequenceNo} - {replayEvent.nodeId ?? "no-node"}
                      </p>
                    </>
                  ) : (
                    <p className="text-xs text-muted-foreground">
                      Nenhum evento rico registrado ainda.
                    </p>
                  )}
                </div>
                <InfoRow icon={GitBranch} label="trace" value={run?.traceId ?? "n/a"} />
              </CardContent>
            </Card>

            <Card className="shadow-none">
              <CardHeader className="p-3 pb-1">
                <CardTitle>Eventos tecnicos</CardTitle>
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
                      <div
                        className="rounded-md border bg-background p-3"
                        key={event.id}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-medium">
                            {event.eventFamily}.{event.eventName}
                          </span>
                          <Badge variant={statusBadgeVariant(event.status)}>
                            {event.status}
                          </Badge>
                        </div>
                        <p className="mt-1 text-muted-foreground">
                          {event.actorName ?? "runtime"} - seq {event.sequenceNo}
                        </p>
                        {event.toolName ? (
                          <p className="mt-1 text-muted-foreground">
                            tool {event.toolName}
                          </p>
                        ) : null}
                      </div>
                    ))
                )}
              </CardContent>
            </Card>

            <Card className="shadow-none">
              <CardHeader className="p-3 pb-1">
                <CardTitle>Comparacao e contexto</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3 p-3 text-xs">
                <div className="grid gap-2">
                  {(comparisonContext?.architectureDistribution ?? []).map((entry) => (
                    <div
                      className="rounded-md border bg-background p-3"
                      key={entry.key}
                    >
                      <p className="font-medium">{entry.key}</p>
                      <p className="mt-1 text-muted-foreground">
                        {entry.count} runs - media{" "}
                        {formatDuration(entry.averageRunDurationMs)}
                      </p>
                    </div>
                  ))}
                </div>
                <div className="rounded-md border bg-background p-3">
                  <p className="font-medium">Peer runs</p>
                  <p className="mt-1 text-muted-foreground">
                    {(comparisonContext?.peerRuns ?? []).length} execucoes relacionadas ao mesmo cenario ou arquitetura.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function RuntimeVisual({
  activeActorName,
  architectureMode,
  actors,
  handoffs,
  stages,
}: {
  activeActorName: string;
  architectureMode: ArchitectureMode;
  actors: unknown[];
  handoffs: unknown[];
  stages: unknown[];
}) {
  if (architectureMode === "structured_workflow") {
    return (
      <WorkflowVisual
        activeActorName={activeActorName}
        stages={stages}
      />
    );
  }
  if (architectureMode === "decentralized_swarm") {
    return (
      <SwarmVisual
        activeActorName={activeActorName}
        actors={actors}
        handoffs={handoffs}
      />
    );
  }
  return (
    <CentralizedVisual
      activeActorName={activeActorName}
      actors={actors}
    />
  );
}

function CentralizedVisual({
  activeActorName,
  actors,
}: {
  activeActorName: string;
  actors: unknown[];
}) {
  const supervisor = toFlowNode(
    actors.find((actor) => getActorName(actor) === "supervisor_agent"),
    "supervisor_agent",
    activeActorName,
    "info",
  );
  const specialists = [
    "faq_agent",
    "stock_agent",
    "image_intake_agent",
  ].map((name) =>
    toFlowNode(
      actors.find((actor) => getActorName(actor) === name),
      name,
      activeActorName,
    ),
  );
  const responseNode = toSyntheticNode(
    "response_streamer",
    activeActorName,
    "response.partial",
  );

  return (
    <div className="grid gap-3 lg:grid-cols-[1fr_auto_1.3fr_auto_1fr] lg:items-center">
      <FlowNodeCard description="coordena e roteia" node={supervisor} />
      <FlowArrow />
      <div className="grid gap-2">
        {specialists.map((node) => (
          <FlowNodeCard
            description="especialista acionado sob demanda"
            key={node.actorName}
            node={node}
          />
        ))}
      </div>
      <FlowArrow />
      <FlowNodeCard description="sintese da resposta" node={responseNode} />
    </div>
  );
}

function WorkflowVisual({
  activeActorName,
  stages,
}: {
  activeActorName: string;
  stages: unknown[];
}) {
  const sequence = [
    { stage: "classify", fallbackActor: "router_agent" },
    { stage: "gather_evidence", fallbackActor: "workflow_evidence_agent" },
    { stage: "multimodal_analysis", fallbackActor: "workflow_multimodal_agent" },
    { stage: "review_gate", fallbackActor: "workflow_review_agent" },
    { stage: "synthesize", fallbackActor: "workflow_synthesis_agent" },
  ];

  return (
    <div className="flex flex-wrap items-center gap-2">
      {sequence.map((step, index) => {
        const matching = stages
          .filter((entry) => getStage(entry) === step.stage)
          .at(-1);
        const node = toFlowNode(
          matching,
          step.fallbackActor,
          activeActorName,
          matching ? undefined : "muted",
        );

        return (
          <div className="flex items-center gap-2" key={step.stage}>
            <FlowNodeCard description={humanizeStage(step.stage)} node={node} />
            {index < sequence.length - 1 ? <FlowArrow /> : null}
          </div>
        );
      })}
    </div>
  );
}

function SwarmVisual({
  activeActorName,
  actors,
  handoffs,
}: {
  activeActorName: string;
  actors: unknown[];
  handoffs: unknown[];
}) {
  const coordinator = toFlowNode(
    actors.find((actor) => getActorName(actor)?.includes("coordinator")),
    "swarm_coordinator",
    activeActorName,
    "info",
  );
  const orbit = dedupeByActor([
    ...actors
      .filter((actor) => getActorName(actor) !== coordinator.actorName)
      .slice(0, 4)
      .map((actor) => toFlowNode(actor, getActorName(actor) ?? "agent", activeActorName)),
    toSyntheticNode("swarm_synthesizer", activeActorName, "swarm.final"),
  ]).slice(0, 4);

  return (
    <div className="grid gap-3">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="grid gap-2">
          {orbit.slice(0, 2).map((node) => (
            <FlowNodeCard
              description="orbita de colaboracao"
              key={node.actorName}
              node={node}
            />
          ))}
        </div>
        <div className="flex items-center justify-center">
          <div className="rounded-3xl border border-primary/20 bg-primary/5 p-3">
            <FlowNodeCard description="coordena handoffs" node={coordinator} />
          </div>
        </div>
        <div className="grid gap-2">
          {orbit.slice(2).map((node) => (
            <FlowNodeCard
              description="agente em mesh"
              key={node.actorName}
              node={node}
            />
          ))}
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {handoffs.length === 0 ? (
          <Badge variant="muted">Nenhum handoff registrado</Badge>
        ) : (
          handoffs.slice(-5).map((handoff, index) => (
            <Badge key={index} variant="outline">
              {getFromTo(handoff)}
            </Badge>
          ))
        )}
      </div>
    </div>
  );
}

function SummaryMetric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Bot;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-primary/10 bg-background/80 p-3 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-primary/10 p-2 text-primary">
          <Icon className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{value}</p>
          <p className="text-[11px] text-muted-foreground">{label}</p>
        </div>
      </div>
    </div>
  );
}

function InfoRow({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Bot;
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
    return <Badge variant="info">tool</Badge>;
  }
  if (event.eventFamily === "handoff") {
    return <Badge variant="warning">handoff</Badge>;
  }
  if (event.eventFamily === "review") {
    return <Badge variant="destructive">review</Badge>;
  }
  if (event.eventFamily === "response") {
    return <Badge variant="success">response</Badge>;
  }
  return <Badge variant="muted">{event.eventFamily}</Badge>;
}

function FlowNodeCard({
  node,
  description,
}: {
  node: FlowNodeData;
  description: string;
}) {
  return (
    <div
      className={`rounded-xl border px-4 py-3 transition-colors ${
        node.active
          ? "border-primary bg-primary/10 shadow-sm"
          : node.tone === "muted"
            ? "border-dashed border-border/70 bg-muted/20"
            : "border-border bg-background"
      }`}
    >
      <div className="flex items-center gap-2">
        <div
          className={`h-2.5 w-2.5 rounded-full ${
            node.active
              ? "bg-primary"
              : node.status === "completed"
                ? "bg-emerald-500"
                : node.status === "running"
                  ? "bg-amber-500"
                  : node.status === "failed"
                    ? "bg-destructive"
                    : "bg-muted-foreground/50"
          }`}
        />
        <p className="text-sm font-semibold">{node.actorName}</p>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">{description}</p>
      <div className="mt-2 flex items-center gap-2">
        <Badge variant={node.tone ?? statusBadgeVariant(node.status)}>{node.status}</Badge>
        {node.nodeId ? (
          <span className="truncate text-[11px] text-muted-foreground">
            {node.nodeId}
          </span>
        ) : null}
      </div>
    </div>
  );
}

function FlowArrow() {
  return (
    <div className="flex items-center justify-center text-muted-foreground">
      <ArrowRight className="h-4 w-4" />
    </div>
  );
}

function toFlowNode(
  raw: unknown,
  fallbackActor: string,
  activeActorName: string,
  tone?: BadgeProps["variant"],
): FlowNodeData {
  return {
    actorName: getActorName(raw) ?? fallbackActor,
    status: getStatus(raw),
    nodeId: getNodeId(raw),
    tone,
    active: (getActorName(raw) ?? fallbackActor) === activeActorName,
  };
}

function toSyntheticNode(
  actorName: string,
  activeActorName: string,
  nodeId: string,
): FlowNodeData {
  return {
    actorName,
    status: actorName === activeActorName ? "running" : "pending",
    nodeId,
    tone: actorName === activeActorName ? "info" : "muted",
    active: actorName === activeActorName,
  };
}

function dedupeByActor(nodes: FlowNodeData[]): FlowNodeData[] {
  const byActor = new Map<string, FlowNodeData>();
  for (const node of nodes) {
    byActor.set(node.actorName, node);
  }
  return Array.from(byActor.values());
}

function readMetricNumber(
  metrics: JsonObject | undefined,
  key: string,
): number {
  const value = metrics?.[key];
  return typeof value === "number" ? value : 0;
}

function getActorName(value: unknown): string | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const raw = (value as Record<string, unknown>).actorName;
  return typeof raw === "string" ? raw : null;
}

function getStatus(value: unknown): string {
  if (!value || typeof value !== "object") {
    return "pending";
  }
  const raw =
    (value as Record<string, unknown>).status ??
    (value as Record<string, unknown>).lastStatus;
  return typeof raw === "string" ? raw : "pending";
}

function getNodeId(value: unknown): string | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const raw = (value as Record<string, unknown>).nodeId;
  return typeof raw === "string" ? raw : null;
}

function getStage(value: unknown): string | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const raw = (value as Record<string, unknown>).stage;
  return typeof raw === "string" ? raw : null;
}

function getFromTo(value: unknown): string {
  if (!value || typeof value !== "object") {
    return "handoff";
  }
  const payload = (value as Record<string, unknown>).payload;
  if (!payload || typeof payload !== "object") {
    return "handoff";
  }
  const from = (payload as Record<string, unknown>).from;
  const to = (payload as Record<string, unknown>).to;
  if (typeof from === "string" && typeof to === "string") {
    return `${from} → ${to}`;
  }
  const actorName = (value as Record<string, unknown>).actorName;
  return typeof actorName === "string" ? actorName : "handoff";
}

function humanizeStage(stage: string): string {
  return stage.replaceAll("_", " ");
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
    return "workflow";
  }
  if (mode === "decentralized_swarm") {
    return "swarm";
  }
  return "centralized";
}

function formatDuration(value: number | null | undefined): string {
  if (typeof value !== "number") {
    return "n/a";
  }
  return `${value} ms`;
}

function shortId(value: string): string {
  return value.slice(0, 8);
}
