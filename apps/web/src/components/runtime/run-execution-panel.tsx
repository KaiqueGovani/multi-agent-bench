"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Bot,
  Clock3,
  GitBranch,
  Loader2,
  Network,
  Pause,
  Play,
  Route,
  ShieldAlert,
  Sparkles,
  Timer,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useRunExecution } from "@/hooks/use-run-execution";
import type { ArchitectureMode, Run } from "@/lib/types";

interface RunExecutionPanelProps {
  runs: Run[];
  selectedRunId: string | null;
  onSelectRun: (runId: string) => void;
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

  const replayEvent = executionEvents[Math.min(replayIndex, Math.max(executionEvents.length - 1, 0))];
  const architectureMode = (projection?.architectureMode ?? run?.experiment?.architectureKey ?? "centralized_orchestration") as ArchitectureMode;
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

  return (
    <section className="border-b bg-card/60">
      <div className="mx-auto grid w-full max-w-7xl gap-3 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <h2 className="text-sm font-semibold">Execucao do runtime</h2>
              <Badge variant="outline">{formatArchitecture(architectureMode)}</Badge>
              <Badge variant={connectionStatus === "open" ? "success" : "warning"}>
                {connectionStatus}
              </Badge>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Visao run-centric com projeção materializada, replay e leitura específica por arquitetura.
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
              disabled={executionEvents.length === 0}
              onClick={() => setIsReplayPlaying((current) => !current)}
              size="sm"
              type="button"
              variant="outline"
            >
              {isReplayPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
              Replay
            </Button>
          </div>
        </div>

        {error ? (
          <Card className="border-destructive bg-destructive/10 shadow-none">
            <CardContent className="p-3 text-sm text-destructive">{error}</CardContent>
          </Card>
        ) : null}

        <div className="grid gap-3 xl:grid-cols-[1.4fr_1fr]">
          <div className="grid gap-3">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard icon={Route} label="status" value={run?.status ?? "n/a"} />
              <MetricCard icon={Bot} label="ator ativo" value={projection?.activeActorName ?? activeEvent?.actorName ?? "n/a"} />
              <MetricCard icon={Timer} label="latencia" value={formatDuration(run?.totalDurationMs)} />
              <MetricCard icon={Activity} label="tokens" value={formatTokens(run?.summary)} />
            </div>

            <Card className="shadow-none">
              <CardHeader className="p-3 pb-1">
                <CardTitle>Mapa da arquitetura</CardTitle>
              </CardHeader>
              <CardContent className="p-3">
                {architectureMode === "centralized_orchestration" ? (
                  <CentralizedView actors={actors} />
                ) : architectureMode === "structured_workflow" ? (
                  <WorkflowView stages={stages} />
                ) : (
                  <SwarmView actors={actors} handoffs={handoffs} />
                )}
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-3">
            <Card className="shadow-none">
              <CardHeader className="p-3 pb-1">
                <CardTitle>Replay e leitura rapida</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3 p-3 text-sm">
                <div className="grid gap-1 rounded-md border bg-background p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">Evento atual</span>
                    <Badge variant="outline">
                      {replayEvent ? `${replayIndex + 1}/${executionEvents.length}` : "0/0"}
                    </Badge>
                  </div>
                  {replayEvent ? (
                    <>
                      <p className="text-foreground">
                        {replayEvent.eventFamily}.{replayEvent.eventName}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {replayEvent.actorName ?? "runtime"} - {replayEvent.status}
                      </p>
                    </>
                  ) : (
                    <p className="text-xs text-muted-foreground">Nenhum evento rico registrado ainda.</p>
                  )}
                </div>

                <div className="grid gap-2 text-xs">
                  <InfoRow icon={Clock3} label="fase" value={projection?.currentPhase ?? "n/a"} />
                  <InfoRow icon={GitBranch} label="trace" value={run?.traceId ?? "n/a"} />
                  <InfoRow icon={Network} label="peer runs" value={String(comparisonContext?.peerRuns.length ?? 0)} />
                  <InfoRow icon={ShieldAlert} label="review" value={run?.humanReviewRequired ? "required" : "clear"} />
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-none">
              <CardHeader className="p-3 pb-1">
                <CardTitle>Ultimos eventos</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-2 p-3 text-xs">
                {executionEvents.length === 0 ? (
                  <p className="text-muted-foreground">Aguardando execução rica do runtime.</p>
                ) : (
                  executionEvents.slice(-6).reverse().map((event) => (
                    <div className="rounded-md border bg-background p-2" key={event.id}>
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium">
                          {event.eventFamily}.{event.eventName}
                        </span>
                        <Badge variant="outline">{event.status}</Badge>
                      </div>
                      <p className="mt-1 text-muted-foreground">
                        {event.actorName ?? "runtime"} - seq {event.sequenceNo}
                      </p>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </section>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Bot;
  label: string;
  value: string;
}) {
  return (
    <Card className="shadow-none">
      <CardContent className="flex items-center gap-3 p-3">
        <Icon className="h-4 w-4 text-primary" />
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{value}</p>
          <p className="text-[11px] text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
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

function CentralizedView({ actors }: { actors: unknown[] }) {
  return (
    <div className="grid gap-3 lg:grid-cols-[1fr_auto_1fr] lg:items-center">
      <ActorCard accent="border-primary" actor={{ actorName: "supervisor_agent", lastStatus: "running" }} />
      <div className="hidden items-center justify-center lg:flex">
        <div className="h-px w-12 bg-border" />
      </div>
      <div className="grid gap-2">
        {actors.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhum especialista materializado ainda.</p>
        ) : (
          actors
            .filter((actor) => getActorName(actor) !== "supervisor_agent")
            .map((actor) => <ActorCard actor={actor} key={getActorName(actor)} />)
        )}
      </div>
    </div>
  );
}

function WorkflowView({ stages }: { stages: unknown[] }) {
  const grouped = ["classify", "gather_evidence", "multimodal_analysis", "review_gate", "synthesize"];
  return (
    <div className="grid gap-3 md:grid-cols-5">
      {grouped.map((stage) => {
        const hits = stages.filter((entry) => getStage(entry) === stage);
        return (
          <div className="rounded-md border bg-background p-3" key={stage}>
            <p className="text-xs font-semibold uppercase text-muted-foreground">{stage}</p>
            <div className="mt-2 grid gap-2">
              {hits.length === 0 ? (
                <p className="text-xs text-muted-foreground">aguardando</p>
              ) : (
                hits.slice(-3).map((entry, index) => (
                  <div className="rounded border bg-muted/30 p-2 text-xs" key={`${stage}-${index}`}>
                    <p className="font-medium">{getActorName(entry) ?? "stage"}</p>
                    <p className="text-muted-foreground">{getStatus(entry)}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SwarmView({ actors, handoffs }: { actors: unknown[]; handoffs: unknown[] }) {
  return (
    <div className="grid gap-3 lg:grid-cols-[1fr_1fr]">
      <div className="grid gap-2">
        {actors.length === 0 ? (
          <p className="text-sm text-muted-foreground">Sem agentes ativos ainda.</p>
        ) : (
          actors.map((actor) => <ActorCard actor={actor} key={getActorName(actor)} />)
        )}
      </div>
      <div className="rounded-md border bg-background p-3">
        <p className="text-xs font-semibold uppercase text-muted-foreground">Handoffs</p>
        <div className="mt-2 grid gap-2">
          {handoffs.length === 0 ? (
            <p className="text-xs text-muted-foreground">Nenhum handoff registrado.</p>
          ) : (
            handoffs.slice(-8).map((handoff, index) => (
              <div className="rounded border bg-muted/30 p-2 text-xs" key={index}>
                <p className="font-medium">{getFromTo(handoff)}</p>
                <p className="text-muted-foreground">{getStatus(handoff)}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function ActorCard({ actor, accent }: { actor: unknown; accent?: string }) {
  return (
    <div className={`rounded-md border bg-background p-3 ${accent ?? ""}`}>
      <p className="text-sm font-semibold">{getActorName(actor) ?? "agent"}</p>
      <p className="mt-1 text-xs text-muted-foreground">
        {getNodeId(actor) ?? "no-node"} - {getStatus(actor)}
      </p>
    </div>
  );
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
    return "n/a";
  }
  const raw = (value as Record<string, unknown>).status ?? (value as Record<string, unknown>).lastStatus;
  return typeof raw === "string" ? raw : "n/a";
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
    return `${from} -> ${to}`;
  }
  return "handoff";
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

function formatTokens(summary: Run["summary"] | undefined): string {
  const total = summary?.totalTokens;
  return typeof total === "number" ? String(total) : "n/a";
}

function shortId(value: string): string {
  return value.slice(0, 8);
}
