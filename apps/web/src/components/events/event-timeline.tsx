"use client";

import type * as React from "react";
import { useId, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  ArrowDown,
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
  Radio,
  Wrench,
  ShieldCheck,
  UserCheck,
  XCircle,
  type LucideIcon
} from "lucide-react";

import { formatActorLabel, formatArchitectureLabel } from "@/components/runtime/presentation";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type {
  ArchitectureMode,
  JsonValue,
  ProcessingEvent,
  ProcessingStatus
} from "@/lib/types";

interface EventTimelineProps {
  events: ProcessingEvent[];
  connectionStatus: string;
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

const statusLabels: Record<ProcessingStatus, string> = {
  completed: "Concluído",
  running: "Em execução",
  failed: "Falhou",
  human_review_required: "Revisão humana",
  pending: "Pendente",
  waiting: "Aguardando"
};

const eventTime = new Intl.DateTimeFormat("pt-BR", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit"
});

const dateTime = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "medium"
});

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

const payloadLabels: Record<string, string> = {
  toolName: "Ferramenta",
  reason: "Motivo",
  route: "Rota",
  handledBy: "Atendido por",
  targetActor: "Destino",
  reviewRequired: "Revisão humana",
  contentText: "Resposta",
  filename: "Arquivo",
  mimeType: "Tipo de arquivo",
  totalTokens: "Tokens",
  error: "Erro"
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
  reviewPanel
}: EventTimelineProps) {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const [followLatest, setFollowLatest] = useState(true);
  const [detailMode, setDetailMode] = useState<TimelineDetailMode>("summary");
  const [filters, setFilters] = useState<TimelineFilters>(initialFilters);
  const liveEventIds = useMemo(() => findLiveEventIds(events), [events]);
  const filterOptions = useMemo(() => buildFilterOptions(events), [events]);
  const filteredEvents = useMemo(
    () => events.filter((event) => matchesFilters(event, filters)),
    [events, filters]
  );
  const liveCount = filteredEvents.filter((event) => liveEventIds.has(event.id)).length;
  const hasActiveFilters = Object.values(filters).some((value) => value !== "all");
  const latestEventId = filteredEvents.at(-1)?.id;

  useLayoutEffect(() => {
    const viewport = viewportRef.current;
    if (viewport && followLatest) {
      viewport.scrollTop = viewport.scrollHeight;
    }
  }, [detailMode, filteredEvents.length, followLatest, latestEventId]);

  function updateFilter(key: keyof TimelineFilters, value: string) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function resetFilters() {
    setFilters(initialFilters);
    setDetailMode("summary");
  }

  return (
    <section
      aria-labelledby="activity-title"
      className="flex min-h-0 flex-1 flex-col bg-background"
      data-testid="activity-panel"
    >
      <div className="shrink-0 border-b bg-card">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-3 py-3 sm:px-5">
          <div className="min-w-0">
            <h2 id="activity-title" className="flex items-center gap-2 text-sm font-semibold">
              <Activity aria-hidden="true" className="h-4 w-4 text-primary" />
              Atividade da conversa
            </h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {events.length === 0
                ? formatArchitectureLabel(architectureMode)
                : `${filteredEvents.length} de ${events.length} eventos · ${liveCount} ${liveCount === 1 ? "etapa ativa" : "etapas ativas"}`}
            </p>
          </div>
          <Badge
            aria-live="polite"
            className="gap-1"
            variant={connectionVariants[connectionStatus] ?? "muted"}
          >
            <ConnectionIcon status={connectionStatus} />
            {connectionLabels[connectionStatus] ?? connectionStatus}
          </Badge>
          {events.length > 0 ? (
            <TimelineFiltersPanel
              detailMode={detailMode}
              filters={filters}
              followLatest={followLatest}
              hasActiveFilters={hasActiveFilters}
              onDetailModeChange={setDetailMode}
              onFilterChange={updateFilter}
              onFollowChange={setFollowLatest}
              onReset={resetFilters}
              options={filterOptions}
            />
          ) : null}
        </div>
      </div>
      {reviewPanel ? (
        <div className="max-h-[32vh] shrink-0 overflow-y-auto border-b bg-card">{reviewPanel}</div>
      ) : null}
      <div
        aria-label="Histórico de eventos"
        className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 py-3 sm:px-5"
        data-testid="activity-scroll"
        onScroll={(event) => {
          const { clientHeight, scrollHeight, scrollTop } = event.currentTarget;
          if (scrollHeight - scrollTop - clientHeight > 24) setFollowLatest(false);
        }}
        ref={viewportRef}
        role="region"
        tabIndex={0}
      >
        <div className="mx-auto max-w-6xl">
          {events.length === 0 ? (
            <Alert>
              <AlertDescription>
                Os eventos aparecem aqui quando uma mensagem é processada.
              </AlertDescription>
            </Alert>
          ) : filteredEvents.length === 0 ? (
            <Alert>
              <AlertDescription>
                Nenhum evento corresponde aos filtros atuais.
              </AlertDescription>
            </Alert>
          ) : (
            <ol className="relative space-y-2 border-l pl-3 sm:pl-4">
              {filteredEvents.map((event) => (
                <EventRow
                  detailed={detailMode === "detailed"}
                  event={event}
                  isLive={liveEventIds.has(event.id)}
                  key={event.id}
                  onExpand={() => setFollowLatest(false)}
                />
              ))}
            </ol>
          )}
        </div>
      </div>
    </section>
  );
}

function EventRow({
  detailed,
  event,
  isLive,
  onExpand,
}: {
  detailed: boolean;
  event: ProcessingEvent;
  isLive: boolean;
  onExpand: () => void;
}) {
  const payloadId = useId();
  const [isExpanded, setIsExpanded] = useState(false);
  const eventName = getEventName(event);
  const EventIcon = eventIcon(eventName);
  const eventRunId = getEventRunId(event);
  const architecture = readPayloadString(event.payload.architectureMode);
  const runtimeMode = readPayloadString(event.payload.runtimeMode);
  const payloadSummary = summarizePayload(event);
  const historical = !isLive && isActiveStatus(event.status);
  const variant = historical ? "muted" : statusVariants[event.status];
  const statusLabel = historical ? "Registrado" : statusLabels[event.status];

  return (
    <li className="relative" data-testid="activity-event">
      <span aria-hidden="true" className={eventDotClass(historical ? "pending" : event.status)} />
      <Card className={`${eventCardAccent(event, historical ? "pending" : event.status)} border-l-4 shadow-none`}>
        <CardHeader className="p-3 pb-1">
          <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1">
            <div className="flex min-w-0 gap-2">
              <EventIcon aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
              <div className="min-w-0">
                <CardTitle className="break-all text-sm">{eventName}</CardTitle>
                {event.actorName ? (
                  <p className="break-words text-xs text-muted-foreground" title={event.actorName}>
                    {formatActorLabel(event.actorName)}
                  </p>
                ) : null}
              </div>
            </div>
            <Badge className="shrink-0 gap-1" variant={variant}>
              <StatusIcon isLive={isLive} status={event.status} />
              {statusLabel}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="grid min-w-0 gap-1 p-3 pt-1 text-xs text-muted-foreground">
          <div className="flex flex-wrap gap-x-2 gap-y-1">
            <time dateTime={event.createdAt} title={dateTime.format(new Date(event.createdAt))}>
              {eventTime.format(new Date(event.createdAt))}
            </time>
            {typeof event.durationMs === "number" ? <span>{event.durationMs} ms</span> : null}
            {event.messageId ? <span title={event.messageId}>Mensagem {shortId(event.messageId)}</span> : null}
            {eventRunId ? <span title={eventRunId}>Execução {shortId(eventRunId)}</span> : null}
          </div>
          {detailed ? (
            <div className="flex flex-wrap gap-2 py-1">
              {eventRunId ? <EventMetaBadge label="execução" value={eventRunId} /> : null}
              <EventMetaBadge label="correlação" value={event.correlationId} />
              <EventMetaBadge label="origem" value={getEventSource(event)} />
              <EventMetaBadge label="status original" value={event.status} />
              {architecture ? <EventMetaBadge label="arquitetura" value={formatArchitectureLabel(architecture)} /> : null}
              {runtimeMode ? <EventMetaBadge label="modo" value={runtimeMode === "mock" ? "Simulado" : runtimeMode} /> : null}
              {typeof event.payload.sequenceNo === "number" ? (
                <EventMetaBadge label="sequência" value={String(event.payload.sequenceNo)} />
              ) : null}
            </div>
          ) : null}
          {payloadSummary ? (
            <p className="break-words text-foreground/80">{payloadSummary}</p>
          ) : null}
          <div>
            <Button
              aria-controls={payloadId}
              aria-expanded={isExpanded}
              aria-label={`Dados do evento ${eventName}`}
              className="h-7 gap-1 px-1 text-xs"
              onClick={() => {
                if (!isExpanded) onExpand();
                setIsExpanded(!isExpanded);
              }}
              type="button"
              variant="ghost"
            >
              <ChevronDown aria-hidden="true" className={`h-3.5 w-3.5 motion-safe:transition-transform ${isExpanded ? "rotate-180" : ""}`} />
              Dados do evento
            </Button>
            <div hidden={!isExpanded} id={payloadId}>
              {isExpanded ? (
                <pre
                  aria-label={`JSON de ${eventName}`}
                  className="max-h-52 overflow-auto rounded-md border bg-muted/40 p-2 text-[11px] text-foreground"
                  tabIndex={0}
                >
                  {JSON.stringify(event.payload, null, 2)}
                </pre>
              ) : null}
            </div>
          </div>
        </CardContent>
      </Card>
    </li>
  );
}

function TimelineFiltersPanel({
  detailMode,
  filters,
  followLatest,
  hasActiveFilters,
  onDetailModeChange,
  onFilterChange,
  onFollowChange,
  onReset,
  options
}: {
  detailMode: TimelineDetailMode;
  filters: TimelineFilters;
  followLatest: boolean;
  hasActiveFilters: boolean;
  onDetailModeChange: (mode: TimelineDetailMode) => void;
  onFilterChange: (key: keyof TimelineFilters, value: string) => void;
  onFollowChange: (value: boolean) => void;
  onReset: () => void;
  options: ReturnType<typeof buildFilterOptions>;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const filtersId = useId();
  const selectors: Array<[keyof TimelineFilters, string, typeof options.runIds]> = [
    ["runId", "Execução", options.runIds],
    ["eventType", "Tipo", options.eventTypes],
    ["actorName", "Ator", options.actorNames],
    ["status", "Status registrado", options.statuses],
    ["messageId", "Mensagem", options.messageIds],
    ["source", "Origem", options.sources]
  ];

  return (
    <div className="w-full min-w-0">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          aria-controls={filtersId}
          aria-expanded={isExpanded}
          className="h-8 gap-2 px-2 text-xs"
          onClick={() => setIsExpanded((current) => !current)}
          type="button"
          variant="outline"
        >
          <Filter aria-hidden="true" className="h-3.5 w-3.5 text-primary" />
          Filtros
          {hasActiveFilters ? <Badge variant="info">ativos</Badge> : null}
          <ChevronDown aria-hidden="true" className={`h-3.5 w-3.5 ${isExpanded ? "rotate-180" : ""}`} />
        </Button>
        {hasActiveFilters || detailMode === "detailed" ? (
          <Button className="h-8 px-2 text-xs" onClick={onReset} type="button" variant="ghost">
            Limpar filtros
          </Button>
        ) : null}
        <Button
          aria-pressed={followLatest}
          className="ml-auto h-8 shrink-0 gap-1.5 px-2 text-xs"
          onClick={() => onFollowChange(!followLatest)}
          title="Rolar automaticamente até o evento mais recente"
          type="button"
          variant={followLatest ? "secondary" : "outline"}
        >
          <ArrowDown aria-hidden="true" className="h-3.5 w-3.5" />
          Acompanhar ao vivo
        </Button>
      </div>
      <div hidden={!isExpanded} id={filtersId}>
        <div className="mt-2 grid max-h-[30dvh] grid-cols-2 gap-2 overflow-y-auto rounded-md border bg-background p-3 sm:grid-cols-3 lg:grid-cols-6">
          {selectors.map(([key, label, values]) => (
            <FilterSelect
              key={key}
              label={label}
              onChange={(value) => onFilterChange(key, value)}
              options={values}
              value={filters[key]}
            />
          ))}
          <div className="col-span-full flex gap-1" aria-label="Nível de detalhe" role="group">
            <Button
              aria-pressed={detailMode === "summary"}
              className="h-7 px-2 text-xs"
              onClick={() => onDetailModeChange("summary")}
              type="button"
              variant={detailMode === "summary" ? "secondary" : "ghost"}
            >
              Resumo
            </Button>
            <Button
              aria-pressed={detailMode === "detailed"}
              className="h-7 px-2 text-xs"
              onClick={() => onDetailModeChange("detailed")}
              type="button"
              variant={detailMode === "detailed" ? "secondary" : "ghost"}
            >
              Metadados
            </Button>
          </div>
        </div>
      </div>
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
    <label className="grid min-w-0 gap-1">
      <span className="text-[11px] font-medium uppercase text-muted-foreground">
        {label}
      </span>
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
    <Badge className="max-w-full gap-1 [overflow-wrap:anywhere]" variant="outline">
      <span className="text-muted-foreground">{label}</span>
      <span className="min-w-0">{value}</span>
    </Badge>
  );
}

function buildFilterOptions(events: ProcessingEvent[]) {
  return {
    actorNames: uniqueOptions(events.map((event) => event.actorName ?? null), formatActorLabel),
    eventTypes: uniqueOptions(events.map(getEventName)),
    messageIds: uniqueOptions(events.map((event) => event.messageId ?? null), shortId),
    runIds: uniqueOptions(events.map((event) => getEventRunId(event)), shortId),
    sources: uniqueOptions(events.map((event) => getEventSource(event))),
    statuses: uniqueOptions(events.map((event) => event.status), (value) => statusLabels[value as ProcessingStatus])
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
): boolean {
  if (filters.runId !== "all" && getEventRunId(event) !== filters.runId) {
    return false;
  }
  if (filters.eventType !== "all" && getEventName(event) !== filters.eventType) {
    return false;
  }
  if (filters.actorName !== "all" && event.actorName !== filters.actorName) {
    return false;
  }
  if (filters.status !== "all" && event.status !== filters.status) {
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
  return (
    readPayloadString(event.payload.runId) ?? readPayloadString(event.payload.run_id)
  );
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

function StatusIcon({ isLive, status }: { isLive: boolean; status: ProcessingStatus }) {
  const Icon =
    status === "completed"
      ? CheckCircle2
      : status === "running" && isLive
        ? Loader2
        : status === "failed"
          ? XCircle
          : status === "human_review_required"
            ? AlertTriangle
            : Clock3;

  return (
    <Icon
      aria-hidden="true"
      className={`h-3.5 w-3.5 ${status === "running" && isLive ? "motion-safe:animate-spin" : ""}`}
    />
  );
}

function ConnectionIcon({ status }: { status: string }) {
  if (status === "open") {
    return <Radio aria-hidden="true" className="h-3.5 w-3.5" />;
  }
  if (status === "error") {
    return <XCircle aria-hidden="true" className="h-3.5 w-3.5" />;
  }
  if (status === "connecting" || status === "reconnecting") {
    return <Loader2 aria-hidden="true" className="h-3.5 w-3.5 motion-safe:animate-spin" />;
  }
  return <Clock3 aria-hidden="true" className="h-3.5 w-3.5" />;
}

function getEventName(event: ProcessingEvent): string {
  const family = readPayloadString(event.payload.eventFamily);
  const name = readPayloadString(event.payload.eventName);
  return name && (family === "tool" || family === "model") ? `${family}.${name}` : event.eventType;
}

function eventIcon(eventType: string): LucideIcon {
  if (eventType.startsWith("tool.")) {
    return Wrench;
  }
  if (eventType.startsWith("model.")) {
    return BrainCircuit;
  }
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

function findLiveEventIds(events: ProcessingEvent[]): Set<string> {
  const latestOperations = new Set<string>();
  const terminalRuns = new Set(
    events.filter(isRunTerminalEvent).map((event) => getEventRunId(event) ?? event.correlationId)
  );
  const liveEventIds = new Set<string>();

  // Events arrive in chronological order from the conversation hook.
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const event = events[i];
    const scope = getEventRunId(event) ?? event.correlationId;
    const operationKey = `${scope}:${getOperationKey(event)}`;
    if (!terminalRuns.has(scope) && !latestOperations.has(operationKey) && isActiveStatus(event.status)) {
      liveEventIds.add(event.id);
    }
    latestOperations.add(operationKey);
  }

  return liveEventIds;
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

  return `absolute -left-[18px] top-4 h-3 w-3 rounded-full border-2 border-card sm:-left-[22px] ${color}`;
}

function summarizePayload(event: ProcessingEvent): string {
  const parts = Object.entries(payloadLabels).flatMap(([key, label]) => {
    const value = formatPayloadValue(event.payload[key]);
    return value ? [`${label}: ${value}`] : [];
  });
  return truncate(parts.join(" · "), 180);
}

function formatPayloadValue(value: JsonValue | undefined): string {
  if (typeof value === "string") {
    return value.trim();
  }
  if (typeof value === "boolean") {
    return value ? "Sim" : "Não";
  }
  return typeof value === "number" ? String(value) : "";
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
  const { payload } = event;
  const family = readPayloadString(payload.eventFamily);
  const actor = event.actorName ?? "runtime";
  const nodeId = readPayloadString(payload.nodeId);
  const invocation = readPayloadString(payload.agentInvocationId) ?? readPayloadString(payload.callId);

  if (family === "tool") {
    return `tool:${readPayloadString(payload.toolCallId) ?? readPayloadString(payload.toolName) ?? actor}`;
  }
  if (family === "model") {
    return `model:${readPayloadString(payload.callId) ?? invocation ?? actor}`;
  }
  if (event.eventType.startsWith("processing.")) {
    return "processing";
  }
  if (event.eventType.startsWith("response.")) {
    return "response";
  }
  if (event.eventType.startsWith("review.")) {
    return "review";
  }
  if (event.eventType.startsWith("handoff.")) {
    return `handoff:${readPayloadString(payload.targetActor) ?? actor}`;
  }
  if (event.eventType.startsWith("actor.")) {
    return `actor:${invocation ?? nodeId ?? actor}`;
  }
  return event.eventType.replace(/\.(started|completed)$/, "");
}

function isRunTerminalEvent(event: ProcessingEvent): boolean {
  return (
    event.eventType === "processing.completed"
    || event.eventType === "review.required"
    || (event.status === "failed" && (
      event.payload.eventFamily === "run"
      || event.payload.finalOutcome != null
      || event.actorName === "ai_runtime"
    ))
  );
}
