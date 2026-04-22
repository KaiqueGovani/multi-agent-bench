"use client";

import { useEffect, useMemo, useRef } from "react";

import type { JsonValue, ProcessingEvent, ProcessingStatus } from "@/lib/types";

interface EventTimelineProps {
  events: ProcessingEvent[];
  connectionStatus: string;
}

const statusStyles: Record<string, string> = {
  completed: "border-success bg-green-50 text-success",
  running: "border-action bg-cyan-50 text-action",
  failed: "border-danger bg-red-50 text-danger",
  human_review_required: "border-warning bg-amber-50 text-warning",
  pending: "border-line bg-surface text-muted",
  waiting: "border-warning bg-amber-50 text-warning"
};

const itemAccentStyles: Record<ProcessingStatus, string> = {
  completed: "border-l-success",
  running: "border-l-action",
  failed: "border-l-danger",
  human_review_required: "border-l-warning",
  pending: "border-l-line",
  waiting: "border-l-warning"
};

const connectionStyles: Record<string, string> = {
  closed: "border-line bg-surface text-muted",
  connecting: "border-warning bg-amber-50 text-warning",
  error: "border-danger bg-red-50 text-danger",
  idle: "border-line bg-surface text-muted",
  open: "border-success bg-green-50 text-success"
};

const connectionLabels: Record<string, string> = {
  closed: "desconectado",
  connecting: "conectando",
  error: "erro",
  idle: "inativo",
  open: "conectado"
};

export function EventTimeline({ events, connectionStatus }: EventTimelineProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const counters = useMemo(() => summarizeEvents(events), [events]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [events.length]);

  return (
    <aside className="flex min-h-[320px] flex-col border-t border-line bg-panel lg:min-h-0 lg:border-l lg:border-t-0">
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-ink">Eventos</h2>
          <p className="text-xs text-muted">
            {counters.total === 0
              ? "Timeline operacional"
              : `${counters.total} eventos - ${counters.running} em execucao`}
          </p>
        </div>
        <span
          className={`rounded border px-2 py-1 text-xs ${
            connectionStyles[connectionStatus] ?? connectionStyles.idle
          }`}
        >
          {connectionLabels[connectionStatus] ?? connectionStatus}
        </span>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {events.length === 0 ? (
          <p className="px-1 py-2 text-sm text-muted">Nenhum evento ainda.</p>
        ) : (
          <ol className="space-y-2">
            {events.map((event) => {
              const payloadSummary = summarizePayload(event);

              return (
                <li
                  key={event.id}
                  className={`border-l-2 bg-surface px-3 py-2 ${
                    itemAccentStyles[event.status] ?? "border-l-line"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="break-words text-sm font-medium text-ink">
                        {event.eventType}
                      </p>
                      {event.actorName ? (
                        <p className="text-xs text-muted">{event.actorName}</p>
                      ) : null}
                    </div>
                    <span
                      className={`shrink-0 rounded border px-2 py-1 text-xs ${
                        statusStyles[event.status] ?? "border-line bg-surface text-muted"
                      }`}
                    >
                      {event.status}
                    </span>
                  </div>
                  <div className="mt-2 grid gap-1 text-xs text-muted">
                    <p>
                      {new Date(event.createdAt).toLocaleTimeString("pt-BR")}
                      {typeof event.durationMs === "number"
                        ? ` - ${event.durationMs} ms`
                        : ""}
                    </p>
                    <p>
                      {event.messageId ? `Mensagem ${shortId(event.messageId)}` : "Sem mensagem"}
                      {` - Corr. ${shortId(event.correlationId)}`}
                    </p>
                    {payloadSummary ? (
                      <p className="break-words text-ink/80">{payloadSummary}</p>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ol>
        )}
        <div ref={bottomRef} />
      </div>
    </aside>
  );
}

function summarizeEvents(events: ProcessingEvent[]) {
  return events.reduce(
    (accumulator, event) => {
      accumulator.total += 1;
      if (event.status === "running") {
        accumulator.running += 1;
      }
      return accumulator;
    },
    { running: 0, total: 0 }
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
