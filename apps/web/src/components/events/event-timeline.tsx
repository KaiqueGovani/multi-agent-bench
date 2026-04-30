"use client";

import type * as React from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Bot,
  BrainCircuit,
  ChevronDown,
  CheckCircle2,
  Clock3,
  FileCheck2,
  Filter,
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
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type {
  ArchitectureMode,
  JsonValue,
  ProcessingEvent,
  ProcessingEventType,
  ProcessingStatus
} from "@/lib/types";

interface EventTimelineProps {
  events: ProcessingEvent[];
  connectionStatus: string;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  architectureMode: ArchitectureMode;
  reviewPanel?: React.ReactNode;
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

type TimelineDetailMode = "summary" | "detailed";

interface TimelineFilters {
  actorName: string;
  eventType: string;
  messageId: string;
  runId: string;
  source: string;
  status: string;
}

const initialFilters: TimelineFilters = {
  actorName: "all",
  eventType: "all",
  messageId: "all",
  runId: "all",
  source: "all",
  status: "all"
};

export function EventTimeline({
  architectureMode,
  events,
  connectionStatus,
  isOpen,
  onOpenChange,
  reviewPanel
}: EventTimelineProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const [detailMode, setDetailMode] = useState<TimelineDetailMode>("summary");
  const [expandedEventIds, setExpandedEventIds] = useState<Set<string>>(new Set());
  const [filters, setFilters] = useState<TimelineFilters>(initialFilters);
  const filterOptions = useMemo(() => buildFilterOptions(events), [events]);
  const filteredEvents = useMemo(
    () => events.filter((event) => matchesFilters(event, filters, events)),
    [events, filters]
  );
  const counters = useMemo(() => summarizeEvents(filteredEvents), [filteredEvents]);
  const totalCounters = useMemo(() => summarizeEvents(events), [events]);
  const activeEvent = useMemo(
    () => [...filteredEvents].reverse().find((event) => isEventCurrentlyActive(event, filteredEvents)),
    [filteredEvents]
  );
  const hasActiveFilters = Object.values(filters).some((value) => value !== "all");

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [filteredEvents.length]);

  function updateFilter(key: keyof TimelineFilters, value: string) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function resetFilters() {
    setFilters(initialFilters);
    setDetailMode("summary");
    setExpandedEventIds(new Set());
  }

  function toggleEventPayload(eventId: string) {
    setExpandedEventIds((current) => {
      const next = new Set(current);
      if (next.has(eventId)) {
        next.delete(eventId);
      } else {
        next.add(eventId);
      }
      return next;
    });
  }

  return (
    <aside
      className={`overflow-hidden border-t bg-card lg:flex lg:min-h-0 lg:max-h-none lg:flex-col lg:border-l lg:border-t-0 ${
        isOpen ? "flex min-h-[240px] max-h-[42vh] flex-col" : "hidden lg:flex"
      }`}
    >
      <div className="border-b px-3 py-3">
        <div className="flex items-center justify-between gap-3">
          {isOpen ? (
            <div className="min-w-0">
              <h2 className="flex items-center gap-2 text-sm font-semibold">
                <Activity className="h-4 w-4 text-primary" />
                Eventos
              </h2>
              <p className="text-xs text-muted-foreground">
                {totalCounters.total === 0
                  ? `Timeline operacional - ${formatArchitectureMode(architectureMode)}`
                  : `${counters.total} de ${totalCounters.total} eventos - ${counters.running} em execucao`}
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
        {isOpen && events.length > 0 ? (
          <TimelineFiltersPanel
            detailMode={detailMode}
            filters={filters}
            hasActiveFilters={hasActiveFilters}
            onDetailModeChange={setDetailMode}
            onFilterChange={updateFilter}
            onReset={resetFilters}
            options={filterOptions}
          />
        ) : null}
        {isOpen && activeEvent ? (
          <ThinkingIndicator
            actorName={activeEvent.actorName}
            eventType={activeEvent.eventType}
          />
        ) : null}
      </div>
      {isOpen && reviewPanel ? (
        <div className="border-b bg-card">
          {reviewPanel}
        </div>
      ) : null}
      {isOpen ? (
        <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {events.length === 0 ? (
          <Alert>
            <AlertDescription>Nenhum evento ainda.</AlertDescription>
          </Alert>
        ) : filteredEvents.length === 0 ? (
          <Alert>
            <AlertDescription>Nenhum evento corresponde aos filtros atuais.</AlertDescription>
          </Alert>
        ) : (
          <ol className="relative space-y-3 border-l pl-4">
            {filteredEvents.map((event) => {
              const payloadSummary = summarizePayload(event);
              const EventIcon = eventIcon(event.eventType);
              const eventSource = getEventSource(event);
              const eventRunId = getEventRunId(event);
              const isPayloadExpanded = expandedEventIds.has(event.id);
              const visualStatus = getVisualStatus(event, filteredEvents);

              return (
                <li className="relative" key={event.id}>
                  <span className={eventDotClass(visualStatus)} />
                  <Card className={`${eventCardAccent(event, visualStatus)} border-l-4 shadow-none`}>
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
                          variant={statusVariants[visualStatus] ?? "muted"}
                        >
                          <StatusIcon status={visualStatus} />
                          {visualStatus}
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
                        {detailMode === "detailed" ? (
                          <div className="flex flex-wrap gap-2 pt-1">
                            <EventMetaBadge label="run" value={eventRunId ? shortId(eventRunId) : "n/a"} />
                            <EventMetaBadge label="origem" value={eventSource} />
                            <EventMetaBadge label="ator" value={event.actorName ?? "n/a"} />
                          </div>
                        ) : null}
                        {payloadSummary ? (
                          <p className="break-words text-foreground/80">{payloadSummary}</p>
                        ) : null}
                        <div className="pt-1">
                          <Button
                            className="h-7 px-2 text-[11px]"
                            onClick={() => toggleEventPayload(event.id)}
                            type="button"
                            variant="ghost"
                          >
                            <ChevronDown
                              className={`h-3.5 w-3.5 transition-transform ${
                                isPayloadExpanded ? "rotate-180" : ""
                              }`}
                            />
                            Payload
                          </Button>
                        </div>
                        {isPayloadExpanded ? (
                          <pre className="max-h-52 overflow-auto rounded-md border bg-muted/40 p-2 text-[11px] text-foreground">
                            {JSON.stringify(event.payload, null, 2)}
                          </pre>
                        ) : null}
                    </CardContent>
                  </Card>
                  {isActiveStatus(visualStatus) ? (
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

function TimelineFiltersPanel({
  detailMode,
  filters,
  hasActiveFilters,
  onDetailModeChange,
  onFilterChange,
  onReset,
  options
}: {
  detailMode: TimelineDetailMode;
  filters: TimelineFilters;
  hasActiveFilters: boolean;
  onDetailModeChange: (mode: TimelineDetailMode) => void;
  onFilterChange: (key: keyof TimelineFilters, value: string) => void;
  onReset: () => void;
  options: ReturnType<typeof buildFilterOptions>;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="mt-3 rounded-md border bg-background p-3">
      <div className="flex items-center justify-between gap-2">
        <button
          className="flex min-w-0 flex-1 items-center gap-2 text-left text-xs font-medium"
          onClick={() => setIsExpanded((current) => !current)}
          type="button"
        >
          <Filter className="h-3.5 w-3.5 shrink-0 text-primary" />
          <span>Filtros</span>
          {hasActiveFilters ? <Badge variant="info">ativos</Badge> : null}
          {detailMode === "detailed" ? <Badge variant="outline">detalhado</Badge> : null}
        </button>
        <div className="flex items-center gap-1">
          <Button
            className="h-7 px-2 text-[11px]"
            disabled={!hasActiveFilters && detailMode === "summary"}
            onClick={onReset}
            type="button"
            variant="ghost"
          >
            Limpar
          </Button>
          <Button
            className="h-7 w-7"
            onClick={() => setIsExpanded((current) => !current)}
            size="icon"
            type="button"
            variant="ghost"
          >
            <ChevronDown
              className={`h-3.5 w-3.5 transition-transform ${isExpanded ? "rotate-180" : ""}`}
            />
          </Button>
        </div>
      </div>
      {isExpanded ? (
      <div className="mt-2 grid gap-2">
        <div className="grid grid-cols-2 gap-2">
          <FilterSelect
            label="run"
            onChange={(value) => onFilterChange("runId", value)}
            options={options.runIds}
            value={filters.runId}
          />
          <FilterSelect
            label="tipo"
            onChange={(value) => onFilterChange("eventType", value)}
            options={options.eventTypes}
            value={filters.eventType}
          />
          <FilterSelect
            label="ator"
            onChange={(value) => onFilterChange("actorName", value)}
            options={options.actorNames}
            value={filters.actorName}
          />
          <FilterSelect
            label="status"
            onChange={(value) => onFilterChange("status", value)}
            options={options.statuses}
            value={filters.status}
          />
          <FilterSelect
            label="mensagem"
            onChange={(value) => onFilterChange("messageId", value)}
            options={options.messageIds}
            value={filters.messageId}
          />
          <FilterSelect
            label="origem"
            onChange={(value) => onFilterChange("source", value)}
            options={options.sources}
            value={filters.source}
          />
        </div>
        <div className="grid grid-cols-2 rounded-md border p-1">
          <button
            className={`rounded px-2 py-1 text-xs ${
              detailMode === "summary" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
            }`}
            onClick={() => onDetailModeChange("summary")}
            type="button"
          >
            Resumo
          </button>
          <button
            className={`rounded px-2 py-1 text-xs ${
              detailMode === "detailed" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
            }`}
            onClick={() => onDetailModeChange("detailed")}
            type="button"
          >
            Detalhado
          </button>
        </div>
      </div>
      ) : null}
    </div>
  );
}

function FilterSelect({
  label,
  onChange,
  options,
  value
}: {
  label: string;
  onChange: (value: string) => void;
  options: Array<{ label: string; value: string }>;
  value: string;
}) {
  return (
    <label className="grid gap-1">
      <span className="text-[11px] font-medium uppercase text-muted-foreground">{label}</span>
      <select
        className="h-8 min-w-0 rounded-md border bg-background px-2 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
        onChange={(event) => onChange(event.target.value)}
        value={value}
      >
        <option value="all">Todos</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function EventMetaBadge({ label, value }: { label: string; value: string }) {
  return (
    <Badge className="gap-1" variant="outline">
      <span className="text-muted-foreground">{label}</span>
      {value}
    </Badge>
  );
}

function buildFilterOptions(events: ProcessingEvent[]) {
  return {
    actorNames: uniqueOptions(events.map((event) => event.actorName ?? null)),
    eventTypes: uniqueOptions(events.map((event) => event.eventType)),
    messageIds: uniqueOptions(events.map((event) => event.messageId ?? null), shortId),
    runIds: uniqueOptions(events.map((event) => getEventRunId(event)), shortId),
    sources: uniqueOptions(events.map((event) => getEventSource(event))),
    statuses: uniqueOptions(events.map((event) => getVisualStatus(event, events)))
  };
}

function uniqueOptions(
  values: Array<string | null | undefined>,
  labelFormatter: (value: string) => string = (value) => value
) {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value))))
    .sort((left, right) => left.localeCompare(right))
    .map((value) => ({ label: labelFormatter(value), value }));
}

function matchesFilters(
  event: ProcessingEvent,
  filters: TimelineFilters,
  allEvents: ProcessingEvent[],
): boolean {
  if (filters.runId !== "all" && getEventRunId(event) !== filters.runId) {
    return false;
  }
  if (filters.eventType !== "all" && event.eventType !== filters.eventType) {
    return false;
  }
  if (filters.actorName !== "all" && event.actorName !== filters.actorName) {
    return false;
  }
  if (filters.status !== "all" && getVisualStatus(event, allEvents) !== filters.status) {
    return false;
  }
  if (filters.messageId !== "all" && event.messageId !== filters.messageId) {
    return false;
  }
  if (filters.source !== "all" && getEventSource(event) !== filters.source) {
    return false;
  }
  return true;
}

function getEventRunId(event: ProcessingEvent): string | null {
  return readPayloadString(event.payload.runId) ?? readPayloadString(event.payload.run_id);
}

function getEventSource(event: ProcessingEvent): string {
  return readPayloadString(event.payload.source) ?? "chat_api";
}

function readPayloadString(value: JsonValue | undefined): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function eventCardAccent(
  event: ProcessingEvent,
  visualStatus: ProcessingStatus,
): string {
  const source = getEventSource(event);
  if (source !== "chat_api" && source !== "mock_runtime") {
    return "border-l-violet-700";
  }
  return itemAccentStyles[visualStatus] ?? "border-l-border";
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

function isTerminalStatus(status: ProcessingStatus): boolean {
  return (
    status === "completed"
    || status === "failed"
    || status === "human_review_required"
  );
}

function isEventCurrentlyActive(
  event: ProcessingEvent,
  allEvents: ProcessingEvent[],
): boolean {
  if (!isActiveStatus(event.status)) {
    return false;
  }

  for (const candidate of allEvents) {
    if (candidate.id === event.id) {
      continue;
    }
    if (!isAfter(candidate, event)) {
      continue;
    }
    if (!belongsToSameRun(candidate, event)) {
      continue;
    }
    if (isRunTerminalEvent(candidate)) {
      return false;
    }
  }

  const operationKey = getOperationKey(event);
  for (const candidate of allEvents) {
    if (candidate.id === event.id) {
      continue;
    }
    if (getOperationKey(candidate) !== operationKey) {
      continue;
    }
    if (!isAfter(candidate, event)) {
      continue;
    }
    if (isTerminalStatus(candidate.status) || isActiveStatus(candidate.status)) {
      return false;
    }
  }
  return true;
}

function getVisualStatus(
  event: ProcessingEvent,
  allEvents: ProcessingEvent[],
): ProcessingStatus {
  if (isActiveStatus(event.status) && !isEventCurrentlyActive(event, allEvents)) {
    return "completed";
  }
  return event.status;
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
      const visualStatus = getVisualStatus(event, events);
      accumulator.total += 1;
      if (visualStatus === "running" || visualStatus === "waiting" || visualStatus === "pending") {
        accumulator.running += 1;
      }
      if (visualStatus === "completed") {
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

function getOperationKey(event: ProcessingEvent): string {
  const nodeId = readPayloadString(event.payload.nodeId);
  if (nodeId) {
    return `${event.correlationId}:node:${nodeId}`;
  }

  const runId = getEventRunId(event);
  if (event.actorName) {
    return `${runId ?? event.correlationId}:actor:${event.actorName}`;
  }

  if (event.eventType.startsWith("processing.")) {
    return `${runId ?? event.correlationId}:processing`;
  }
  if (event.eventType.startsWith("response.")) {
    return `${runId ?? event.correlationId}:response`;
  }
  if (event.eventType.startsWith("review.")) {
    return `${runId ?? event.correlationId}:review`;
  }
  if (event.eventType.startsWith("handoff.")) {
    return `${runId ?? event.correlationId}:handoff:${readPayloadString(event.payload.targetActor) ?? "unknown"}`;
  }
  return `${runId ?? event.correlationId}:${event.eventType}`;
}

function isAfter(left: ProcessingEvent, right: ProcessingEvent): boolean {
  const timeDifference =
    new Date(left.createdAt).getTime() - new Date(right.createdAt).getTime();
  return timeDifference === 0 ? left.id > right.id : timeDifference > 0;
}

function belongsToSameRun(left: ProcessingEvent, right: ProcessingEvent): boolean {
  const leftRunId = getEventRunId(left);
  const rightRunId = getEventRunId(right);
  if (leftRunId && rightRunId) {
    return leftRunId === rightRunId;
  }
  return left.correlationId === right.correlationId;
}

function isRunTerminalEvent(event: ProcessingEvent): boolean {
  return (
    event.eventType === "processing.completed"
    || event.eventType === "response.final"
    || event.eventType === "review.required"
    || event.status === "failed"
    || event.status === "human_review_required"
  );
}
