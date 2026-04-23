"use client";

import { useEffect, useMemo, useRef } from "react";
import { PanelRightClose, PanelRightOpen } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { JsonValue, ProcessingEvent, ProcessingStatus } from "@/lib/types";

interface EventTimelineProps {
  events: ProcessingEvent[];
  connectionStatus: string;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
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
  events,
  connectionStatus,
  isOpen,
  onOpenChange
}: EventTimelineProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const counters = useMemo(() => summarizeEvents(events), [events]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [events.length]);

  return (
    <aside className="flex min-h-[320px] flex-col border-t bg-card lg:min-h-0 lg:border-l lg:border-t-0">
      <div className="border-b px-3 py-3">
        <div className="flex items-center justify-between gap-3">
          {isOpen ? (
            <div>
              <h2 className="text-sm font-semibold">Eventos</h2>
              <p className="text-xs text-muted-foreground">
                {counters.total === 0
                  ? "Timeline operacional"
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
            <Badge variant={connectionVariants[connectionStatus] ?? "muted"}>
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
            <Metric label="total" value={counters.total} />
            <Metric className="text-sky-700" label="ativos" value={counters.running} />
            <Metric className="text-emerald-700" label="concl." value={counters.completed} />
          </div>
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

              return (
                <li className="relative" key={event.id}>
                  <span className={eventDotClass(event.status)} />
                  <Card className={`${itemAccentStyles[event.status] ?? "border-l-border"} border-l-4 shadow-none`}>
                    <CardHeader className="p-3 pb-1">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <CardTitle className="break-words">{event.eventType}</CardTitle>
                          {event.actorName ? (
                            <p className="text-xs text-muted-foreground">{event.actorName}</p>
                          ) : null}
                        </div>
                        <Badge
                          className="shrink-0"
                          variant={statusVariants[event.status] ?? "muted"}
                        >
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

function Metric({
  className,
  label,
  value
}: {
  className?: string;
  label: string;
  value: number;
}) {
  return (
    <Card className="shadow-none">
      <CardContent className="p-2 text-center">
        <p className={`text-sm font-semibold ${className ?? ""}`}>{value}</p>
        <p className="text-[11px] text-muted-foreground">{label}</p>
      </CardContent>
    </Card>
  );
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
