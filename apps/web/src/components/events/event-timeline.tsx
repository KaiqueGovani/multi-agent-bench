"use client";

import { useEffect, useMemo, useRef } from "react";
import {
  Activity,
  AlertTriangle,
  Bot,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  FileCheck2,
  Loader2,
  MessageCircle,
  MessageSquareReply,
  Paperclip,
  PanelRightClose,
  PanelRightOpen,
  Radio,
  ShieldCheck,
  UserCheck,
  XCircle,
  type LucideIcon
} from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { ArchitectureMode, JsonValue, ProcessingEvent, ProcessingStatus } from "@/lib/types";

interface EventTimelineProps {
  events: ProcessingEvent[];
  connectionStatus: string;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  architectureMode: ArchitectureMode;
}

const statusVariants: Record<string, BadgeProps["variant"]> = {
  completed: "success",
  running: "info",
  failed: "destructive",
  human_review_required: "warning",
  pending: "muted",
  waiting: "warning"
};

const itemAccentStyles: Record<ProcessingStatus, string> = {
  completed: "border-l-emerald-700",
  running: "border-l-sky-700",
  failed: "border-l-destructive",
  human_review_required: "border-l-amber-700",
  pending: "border-l-border",
  waiting: "border-l-amber-700"
};

const connectionVariants: Record<string, BadgeProps["variant"]> = {
  closed: "muted",
  connecting: "warning",
  error: "destructive",
  idle: "muted",
  open: "success",
  reconnecting: "warning"
};

const connectionLabels: Record<string, string> = {
  closed: "desconectado",
  connecting: "conectando",
  error: "erro",
  idle: "inativo",
  open: "conectado",
  reconnecting: "reconectando"
};

export function EventTimeline({
  architectureMode,
  events,
  connectionStatus,
  isOpen,
  onOpenChange
}: EventTimelineProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const counters = useMemo(() => summarizeEvents(events), [events]);
  const activeEvent = useMemo(
    () => [...events].reverse().find((event) => isActiveStatus(event.status)),
    [events]
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [events.length]);

  return (
    <aside className="flex min-h-[320px] flex-col border-t bg-card lg:min-h-0 lg:border-l lg:border-t-0">
      <div className="border-b px-3 py-3">
        <div className="flex items-center justify-between gap-3">
          {isOpen ? (
            <div className="min-w-0">
              <h2 className="flex items-center gap-2 text-sm font-semibold">
                <Activity className="h-4 w-4 text-primary" />
                Eventos
              </h2>
              <p className="text-xs text-muted-foreground">
                {counters.total === 0
                  ? `Timeline operacional - ${formatArchitectureMode(architectureMode)}`
                  : `${counters.total} eventos - ${counters.running} em execucao`}
              </p>
            </div>
          ) : null}
          <button
            className="hidden h-8 w-8 items-center justify-center rounded-md border text-muted-foreground transition-colors hover:bg-muted hover:text-foreground lg:inline-flex"
            onClick={() => onOpenChange(!isOpen)}
            type="button"
          >
            {isOpen ? (
              <PanelRightClose className="h-4 w-4" />
            ) : (
              <PanelRightOpen className="h-4 w-4" />
            )}
          </button>
          {isOpen ? (
            <Badge className="gap-1" variant={connectionVariants[connectionStatus] ?? "muted"}>
              <ConnectionIcon status={connectionStatus} />
              {connectionLabels[connectionStatus] ?? connectionStatus}
            </Badge>
          ) : null}
        </div>
        {!isOpen ? (
          <div className="mt-4 hidden items-center justify-center [writing-mode:vertical-rl] lg:flex">
            <span className="text-xs font-medium text-muted-foreground">Eventos</span>
            {counters.total > 0 ? (
              <Badge className="mt-3 [writing-mode:horizontal-tb]">{counters.total}</Badge>
            ) : null}
          </div>
        ) : null}
        {isOpen && counters.total > 0 ? (
          <div className="mt-3 grid grid-cols-3 gap-2">
            <Metric icon={Activity} label="total" value={counters.total} />
            <Metric className="text-sky-700" icon={Loader2} label="ativos" value={counters.running} />
            <Metric className="text-emerald-700" icon={CheckCircle2} label="concl." value={counters.completed} />
          </div>
        ) : null}
        {isOpen && activeEvent ? (
          <ThinkingIndicator
            actorName={activeEvent.actorName}
            eventType={activeEvent.eventType}
          />
        ) : null}
      </div>
      {isOpen ? (
        <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {events.length === 0 ? (
          <Alert>
            <AlertDescription>Nenhum evento ainda.</AlertDescription>
          </Alert>
        ) : (
          <ol className="relative space-y-3 border-l pl-4">
            {events.map((event) => {
              const payloadSummary = summarizePayload(event);
              const EventIcon = eventIcon(event.eventType);

              return (
                <li className="relative" key={event.id}>
                  <span className={eventDotClass(event.status)} />
                  <Card className={`${itemAccentStyles[event.status] ?? "border-l-border"} border-l-4 shadow-none`}>
                    <CardHeader className="p-3 pb-1">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex min-w-0 gap-2">
                          <EventIcon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                          <div className="min-w-0">
                            <CardTitle className="break-words">{event.eventType}</CardTitle>
                          {event.actorName ? (
                            <p className="text-xs text-muted-foreground">{event.actorName}</p>
                          ) : null}
                          </div>
                        </div>
                        <Badge
                          className="shrink-0 gap-1"
                          variant={statusVariants[event.status] ?? "muted"}
                        >
                          <StatusIcon status={event.status} />
                          {event.status}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="grid gap-1 p-3 pt-1 text-xs text-muted-foreground">
                        <p>
                          {new Date(event.createdAt).toLocaleTimeString("pt-BR")}
                          {typeof event.durationMs === "number"
                            ? ` - ${event.durationMs} ms`
                            : ""}
                        </p>
                        <p>
                          {event.messageId
                            ? `Mensagem ${shortId(event.messageId)}`
                            : "Sem mensagem"}
                          {` - Corr. ${shortId(event.correlationId)}`}
                        </p>
                        {payloadSummary ? (
                          <p className="break-words text-foreground/80">{payloadSummary}</p>
                        ) : null}
                    </CardContent>
                  </Card>
                  {isActiveStatus(event.status) ? (
                    <div className="ml-3 mt-2">
                      <InlineThinking actorName={event.actorName} />
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ol>
        )}
        <div ref={bottomRef} />
        </div>
      ) : null}
    </aside>
  );
}

function formatArchitectureMode(mode: ArchitectureMode): string {
  const labels: Record<ArchitectureMode, string> = {
    centralized_orchestration: "orquestracao centralizada",
    decentralized_swarm: "swarm descentralizado",
    structured_workflow: "workflow estruturado"
  };
  return labels[mode];
}

function Metric({
  className,
  icon: Icon,
  label,
  value
}: {
  className?: string;
  icon: LucideIcon;
  label: string;
  value: number;
}) {
  return (
    <Card className="shadow-none">
      <CardContent className="p-2 text-center">
        <div className="flex items-center justify-center gap-1">
          <Icon className={`h-3.5 w-3.5 ${className ?? ""}`} />
          <p className={`text-sm font-semibold ${className ?? ""}`}>{value}</p>
        </div>
        <p className="text-[11px] text-muted-foreground">{label}</p>
      </CardContent>
    </Card>
  );
}

function ThinkingIndicator({
  actorName,
  eventType
}: {
  actorName: string | null | undefined;
  eventType: string;
}) {
  return (
    <div className="mt-3 rounded-md border bg-background p-3">
      <div className="flex items-center gap-2 text-xs font-medium">
        <Loader2 className="h-4 w-4 animate-spin text-sky-700" />
        <span>{actorName ?? "runtime"} pensando</span>
        <Badge variant="info">{eventType}</Badge>
      </div>
      <div className="mt-3 space-y-2">
        <Skeleton className="h-2 w-11/12" />
        <Skeleton className="h-2 w-8/12" />
      </div>
    </div>
  );
}

function InlineThinking({ actorName }: { actorName: string | null | undefined }) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-dashed bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
      <Loader2 className="h-3.5 w-3.5 animate-spin text-sky-700" />
      <span>{actorName ?? "runtime"} ainda processando</span>
      <span className="flex gap-1" aria-hidden="true">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-sky-700 [animation-delay:-0.2s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-sky-700 [animation-delay:-0.1s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-sky-700" />
      </span>
    </div>
  );
}

function StatusIcon({ status }: { status: ProcessingStatus }) {
  const Icon =
    status === "completed"
      ? CheckCircle2
      : status === "running"
        ? Loader2
        : status === "failed"
          ? XCircle
          : status === "human_review_required"
            ? AlertTriangle
            : Clock3;

  return (
    <Icon
      className={`h-3.5 w-3.5 ${status === "running" ? "animate-spin" : ""}`}
    />
  );
}

function ConnectionIcon({ status }: { status: string }) {
  if (status === "open") {
    return <Radio className="h-3.5 w-3.5" />;
  }
  if (status === "error") {
    return <XCircle className="h-3.5 w-3.5" />;
  }
  if (status === "connecting" || status === "reconnecting") {
    return <Loader2 className="h-3.5 w-3.5 animate-spin" />;
  }
  return <Clock3 className="h-3.5 w-3.5" />;
}

function eventIcon(eventType: string): LucideIcon {
  if (eventType.startsWith("message.")) {
    return MessageCircle;
  }
  if (eventType.startsWith("attachment.upload")) {
    return Paperclip;
  }
  if (eventType.startsWith("attachment.validation")) {
    return ShieldCheck;
  }
  if (eventType.startsWith("processing.")) {
    return BrainCircuit;
  }
  if (eventType === "actor.progress") {
    return Activity;
  }
  if (eventType.startsWith("actor.")) {
    return Bot;
  }
  if (eventType === "review.required") {
    return UserCheck;
  }
  if (eventType.startsWith("response.")) {
    return MessageSquareReply;
  }
  if (eventType === "conversation.created") {
    return FileCheck2;
  }
  return Activity;
}

function isActiveStatus(status: ProcessingStatus): boolean {
  return status === "running" || status === "waiting" || status === "pending";
}

function eventDotClass(status: ProcessingStatus): string {
  const color =
    status === "completed"
      ? "bg-emerald-700"
      : status === "running"
        ? "bg-sky-700"
        : status === "failed"
          ? "bg-destructive"
          : status === "human_review_required"
            ? "bg-amber-700"
            : "bg-muted-foreground";

  return `absolute -left-[22px] top-4 h-3 w-3 rounded-full border-2 border-card ${color}`;
}

function summarizeEvents(events: ProcessingEvent[]) {
  return events.reduce(
    (accumulator, event) => {
      accumulator.total += 1;
      if (event.status === "running") {
        accumulator.running += 1;
      }
      if (event.status === "completed") {
        accumulator.completed += 1;
      }
      return accumulator;
    },
    { completed: 0, running: 0, total: 0 }
  );
}

function summarizePayload(event: ProcessingEvent): string {
  const preferredKeys = [
    "reason",
    "route",
    "handledBy",
    "reviewRequired",
    "totalDurationMs",
    "runtimeMode",
    "architectureMode",
    "contentText"
  ];

  const parts = preferredKeys
    .filter((key) => event.payload[key] !== undefined)
    .map((key) => `${formatPayloadKey(key)}: ${formatPayloadValue(event.payload[key])}`);

  if (parts.length > 0) {
    return truncate(parts.join(" - "), 180);
  }

  const fallback = Object.entries(event.payload)
    .slice(0, 3)
    .map(([key, value]) => `${formatPayloadKey(key)}: ${formatPayloadValue(value)}`);

  return truncate(fallback.join(" - "), 180);
}

function formatPayloadKey(key: string): string {
  return key.replace(/([A-Z])/g, " $1").toLowerCase();
}

function formatPayloadValue(value: JsonValue | undefined): string {
  if (value === undefined) {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value);
}

function shortId(id: string): string {
  return id.slice(0, 8);
}

function truncate(value: string, maxLength: number): string {
  if (value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength - 3)}...`;
}
