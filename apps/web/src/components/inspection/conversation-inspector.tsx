"use client";

import {
  Activity,
  Boxes,
  Check,
  ChevronDown,
  Clipboard,
  Copy,
  Database,
  FileText,
  MessageSquare,
  Route,
  Search,
  ShieldAlert,
  X,
  type LucideIcon
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import type {
  Attachment,
  Conversation,
  JsonObject,
  Message,
  ProcessingEvent,
  ReviewTask,
  Run
} from "@/lib/types";

interface ConversationInspectorProps {
  attachments: Attachment[];
  conversation: Conversation | null;
  events: ProcessingEvent[];
  isOpen: boolean;
  messages: Message[];
  onOpenChange: (open: boolean) => void;
  reviewTasks: ReviewTask[];
  runs: Run[];
}

export function ConversationInspector({
  attachments,
  conversation,
  events,
  isOpen,
  messages,
  onOpenChange,
  reviewTasks,
  runs
}: ConversationInspectorProps) {
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [copiedValue, setCopiedValue] = useState<string | null>(null);
  const latestRun = runs.at(-1) ?? null;
  const totals = useMemo(
    () => ({
      attachments: attachments.length,
      events: events.length,
      messages: messages.length,
      reviewTasks: reviewTasks.length,
      runs: runs.length
    }),
    [attachments.length, events.length, messages.length, reviewTasks.length, runs.length]
  );

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onOpenChange(false);
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onOpenChange]);

  if (!isOpen) {
    return null;
  }

  async function copyValue(value: string | null | undefined) {
    if (!value) {
      return;
    }
    await navigator.clipboard.writeText(value);
    setCopiedValue(value);
    window.setTimeout(() => setCopiedValue(null), 1200);
  }

  return (
    <div
      aria-labelledby="conversation-inspector-title"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-3 backdrop-blur-sm sm:p-6"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onOpenChange(false);
        }
      }}
      role="dialog"
    >
      <section className="flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-lg border bg-background shadow-2xl">
        <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
          <div className="min-w-0">
            <h2
              className="flex items-center gap-2 text-base font-semibold"
              id="conversation-inspector-title"
            >
              <Search className="h-4 w-4 text-primary" />
              Inspecao tecnica
            </h2>
            <p className="truncate text-xs text-muted-foreground">
              IDs, metadados e payloads da conversa ativa
            </p>
          </div>
          <Button
            onClick={() => onOpenChange(false)}
            size="sm"
            type="button"
            variant="outline"
          >
            <X className="h-4 w-4" />
            <span className="hidden sm:inline">Fechar</span>
          </Button>
        </div>

        <div className="grid min-h-0 gap-3 overflow-y-auto p-3 sm:p-4">
          <div className="grid gap-3 xl:grid-cols-[1fr_1fr]">
            <Card className="shadow-none">
              <CardHeader className="p-3 pb-1">
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-4 w-4" />
                  Conversa
                </CardTitle>
              </CardHeader>
              <CardContent className="grid gap-2 p-3 text-xs">
                <Field
                  copied={copiedValue === conversation?.id}
                  label="conversation_id"
                  onCopy={() => copyValue(conversation?.id)}
                  value={conversation?.id}
                />
                <Field label="status" value={conversation?.status} />
                <Field label="channel" value={conversation?.channel} />
                <Field label="updated_at" value={conversation?.updatedAt} />
                <JsonBlock title="metadata operacional" value={conversation?.metadata ?? {}} />
              </CardContent>
            </Card>

            <Card className="shadow-none">
              <CardHeader className="p-3 pb-1">
                <CardTitle className="flex items-center gap-2">
                  <Route className="h-4 w-4" />
                  Run atual
                </CardTitle>
              </CardHeader>
              <CardContent className="grid gap-2 p-3 text-xs">
                <Field
                  copied={copiedValue === latestRun?.id}
                  label="run_id"
                  onCopy={() => copyValue(latestRun?.id)}
                  value={latestRun?.id}
                />
                <Field label="status" value={latestRun?.status} />
                <Field
                  copied={copiedValue === latestRun?.traceId}
                  label="trace_id"
                  onCopy={() => copyValue(latestRun?.traceId)}
                  value={latestRun?.traceId}
                />
                <Field label="external_run_id" value={latestRun?.externalRunId} />
                <Field label="ai_session_id" value={latestRun?.aiSessionId} />
                <Field label="duration_ms" value={latestRun?.totalDurationMs?.toString()} />
                <JsonBlock title="experimento" value={latestRun?.experiment ?? {}} />
                <JsonBlock title="summary" value={latestRun?.summary ?? {}} />
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <Metric icon={MessageSquare} label="mensagens" value={totals.messages} />
            <Metric icon={FileText} label="anexos" value={totals.attachments} />
            <Metric icon={Activity} label="eventos" value={totals.events} />
            <Metric icon={Route} label="runs" value={totals.runs} />
            <Metric icon={ShieldAlert} label="revisoes" value={totals.reviewTasks} />
          </div>

        <Card className="shadow-none">
          <CardHeader className="p-3 pb-1">
            <CardTitle className="flex items-center gap-2">
              <Boxes className="h-4 w-4" />
              Entidades
            </CardTitle>
          </CardHeader>
          <CardContent className="grid items-start gap-3 p-3 text-xs lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)]">
            <EntityList
              copiedValue={copiedValue}
              items={messages.map((message) => ({
                id: message.id,
                meta: `${message.direction} / ${message.status}`,
                title: message.contentText || "(sem texto)"
              }))}
              onCopy={copyValue}
              title="Mensagens"
            />
            <EntityList
              copiedValue={copiedValue}
              items={attachments.map((attachment) => ({
                id: attachment.id,
                meta: `${attachment.mimeType} / ${formatBytes(attachment.sizeBytes)}`,
                title: attachment.originalFilename
              }))}
              onCopy={copyValue}
              title="Anexos"
            />
            <EntityList
              copiedValue={copiedValue}
              items={reviewTasks.map((task) => ({
                id: task.id,
                meta: task.status,
                title: task.reason
              }))}
              onCopy={copyValue}
              title="Revisoes"
            />
          </CardContent>
        </Card>

        <Card className="shadow-none">
          <CardHeader className="p-3 pb-1">
            <CardTitle className="flex items-center gap-2">
              <Clipboard className="h-4 w-4" />
              Eventos e payloads
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 p-3 text-xs">
            {events.length === 0 ? (
              <p className="text-muted-foreground">Nenhum evento registrado.</p>
            ) : (
              events.map((event) => (
                <div className="rounded-md border bg-background" key={event.id}>
                  <button
                    className="flex w-full items-center justify-between gap-3 p-2 text-left"
                    onClick={() =>
                      setExpandedEventId((current) => current === event.id ? null : event.id)
                    }
                    type="button"
                  >
                    <span className="min-w-0 truncate">
                      {event.eventType} / {event.status}
                    </span>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge variant="outline">{shortId(event.id)}</Badge>
                      <ChevronDown className="h-4 w-4" />
                    </div>
                  </button>
                  {expandedEventId === event.id ? (
                    <div className="border-t p-2">
                      <Field
                        copied={copiedValue === event.id}
                        label="event_id"
                        onCopy={() => copyValue(event.id)}
                        value={event.id}
                      />
                      <Field
                        copied={copiedValue === event.correlationId}
                        label="correlation_id"
                        onCopy={() => copyValue(event.correlationId)}
                        value={event.correlationId}
                      />
                      <JsonBlock title="payload_json" value={event.payload} />
                    </div>
                  ) : null}
                </div>
              ))
            )}
          </CardContent>
        </Card>
        </div>
      </section>
    </div>
  );
}

function Field({
  copied,
  label,
  onCopy,
  value
}: {
  copied?: boolean;
  label: string;
  onCopy?: () => void;
  value?: string | null;
}) {
  return (
    <div className="grid gap-1">
      <span className="text-[11px] font-medium uppercase text-muted-foreground">{label}</span>
      <div className="flex min-w-0 items-center gap-2">
        <code className="min-w-0 flex-1 truncate rounded bg-muted px-2 py-1">
          {value ?? "n/a"}
        </code>
        {onCopy ? (
          <Button
            className="h-7 w-7"
            disabled={!value}
            onClick={onCopy}
            size="icon"
            type="button"
            variant="outline"
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function JsonBlock({ title, value }: { title: string; value: JsonObject }) {
  return (
    <details className="rounded-md border bg-background p-2">
      <summary className="cursor-pointer text-[11px] font-medium uppercase text-muted-foreground">
        {title}
      </summary>
      <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-[11px]">
        {JSON.stringify(value, null, 2)}
      </pre>
    </details>
  );
}

function EntityList({
  copiedValue,
  items,
  onCopy,
  title
}: {
  copiedValue: string | null;
  items: Array<{ id: string; meta: string; title: string }>;
  onCopy: (value: string) => void;
  title: string;
}) {
  return (
    <div className="grid min-w-0 content-start gap-2 overflow-hidden">
      <h3 className="text-xs font-semibold">{title}</h3>
      {items.length === 0 ? (
        <div className="rounded-md border border-dashed bg-muted/30 p-3 text-muted-foreground">
          Nenhum registro.
        </div>
      ) : (
        items.map((item) => (
          <div className="min-w-0 overflow-hidden rounded-md border bg-background p-2" key={item.id}>
            <p className="min-w-0 truncate font-medium">{item.title}</p>
            <p className="min-w-0 truncate text-[11px] text-muted-foreground">{item.meta}</p>
            <div className="mt-2 flex min-w-0 items-center gap-2">
              <code className="min-w-0 flex-1 truncate rounded bg-muted px-2 py-1">
                {item.id}
              </code>
              <Button
                className="h-7 w-7"
                onClick={() => onCopy(item.id)}
                size="icon"
                type="button"
                variant="outline"
              >
                {copiedValue === item.id ? (
                  <Check className="h-3.5 w-3.5" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )}
              </Button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

function Metric({
  icon: Icon,
  label,
  value
}: {
  icon: LucideIcon;
  label: string;
  value: number;
}) {
  return (
    <Card className="shadow-none">
      <CardContent className="flex items-center gap-2 p-3">
        <Icon className="h-4 w-4 text-primary" />
        <div>
          <p className="text-sm font-semibold">{value}</p>
          <p className="text-[11px] text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function shortId(id: string): string {
  return id.slice(0, 8);
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const kilobytes = bytes / 1024;
  if (kilobytes < 1024) {
    return `${kilobytes.toFixed(1)} KB`;
  }
  return `${(kilobytes / 1024).toFixed(1)} MB`;
}
