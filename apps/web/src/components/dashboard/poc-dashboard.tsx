"use client";

import { useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  CheckCircle2,
  Clock3,
  ClipboardCheck,
  ClipboardX,
  Database,
  FileText,
  MessageSquare,
  Route,
  ShieldAlert,
  Timer,
  X,
  XCircle,
  type LucideIcon
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getDashboardMetrics } from "@/lib/api/client";
import type {
  DashboardConversationItem,
  DashboardDistributionItem,
  DashboardMetricsResponse,
  ReviewTask
} from "@/lib/types";

interface PocDashboardProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onResolveReviewTask: (
    reviewTaskId: string,
    status: "resolved" | "cancelled" | "in_review",
    note: string
  ) => void;
  reviewTasks: ReviewTask[];
  onSelectConversation: (conversationId: string) => void;
}

export function PocDashboard({
  isOpen,
  onOpenChange,
  onResolveReviewTask,
  reviewTasks,
  onSelectConversation
}: PocDashboardProps) {
  const [metrics, setMetrics] = useState<DashboardMetricsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "reviews">("overview");

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    let isCancelled = false;
    setIsLoading(true);
    setError(null);
    void getDashboardMetrics()
      .then((response) => {
        if (!isCancelled) {
          setMetrics(response);
        }
      })
      .catch((caught) => {
        if (!isCancelled) {
          setError(caught instanceof Error ? caught.message : "Falha ao carregar o painel");
        }
      })
      .finally(() => {
        if (!isCancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [isOpen]);

  const generatedAt = useMemo(() => {
    if (!metrics?.generatedAt) {
      return null;
    }
    return new Date(metrics.generatedAt).toLocaleString("pt-BR", {
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      month: "2-digit"
    });
  }, [metrics?.generatedAt]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      aria-labelledby="poc-dashboard-title"
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
              id="poc-dashboard-title"
            >
              <BarChart3 className="h-4 w-4 text-primary" />
              Dashboard da POC
            </h2>
            <p className="truncate text-xs text-muted-foreground">
              Indicadores operacionais e comparação inicial de configurações
              {generatedAt ? ` - ${generatedAt}` : ""}
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

        <div className="min-h-0 overflow-y-auto p-3 sm:p-4">
          <div className="mb-4 grid grid-cols-2 rounded-md border p-1">
            <button
              className={`rounded px-3 py-2 text-sm ${
                activeTab === "overview"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground"
              }`}
              onClick={() => setActiveTab("overview")}
              type="button"
            >
              Visão geral
            </button>
            <button
              className={`rounded px-3 py-2 text-sm ${
                activeTab === "reviews"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground"
              }`}
              onClick={() => setActiveTab("reviews")}
              type="button"
            >
              Revisões
              {reviewTasks.length > 0 ? ` (${reviewTasks.length})` : ""}
            </button>
          </div>
          {isLoading ? (
            <div className="rounded-md border bg-card p-4 text-sm text-muted-foreground">
              Carregando métricas...
            </div>
          ) : error ? (
            <div className="rounded-md border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
              {error}
            </div>
          ) : activeTab === "overview" && metrics ? (
            <div className="grid gap-4">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <MetricCard icon={MessageSquare} label="conversas" value={metrics.totals.conversations} />
                <MetricCard icon={Route} label="execuções" value={metrics.totals.runs} />
                <MetricCard icon={CheckCircle2} label="execuções concluídas" value={metrics.totals.runsCompleted} />
                <MetricCard icon={XCircle} label="execuções com erro" value={metrics.totals.runsFailed} />
                <MetricCard icon={ShieldAlert} label="execuções com revisão" value={metrics.totals.runsHumanReview} />
                <MetricCard icon={FileText} label="mensagens" value={metrics.totals.messages} />
                <MetricCard icon={Database} label="anexos" value={metrics.totals.attachments} />
                <MetricCard
                  icon={Timer}
                  label="tempo médio"
                  value={formatDuration(metrics.totals.averageRunDurationMs)}
                />
                <MetricCard
                  icon={Clock3}
                  label="p95 latência"
                  value={formatDuration(asNumber(metrics.latencyPercentiles?.p95))}
                />
              </div>

              <div className="grid gap-3 lg:grid-cols-2">
                <DistributionCard title="Por arquitetura" values={metrics.byArchitecture} />
                <DistributionCard title="Por modelo" values={metrics.byModel} />
                <DistributionCard title="Por cenário" values={metrics.byScenario} />
                <DistributionCard title="Por tipo de anexo" values={metrics.byAttachmentType} />
                <DistributionCard title="Por ferramenta" values={metrics.byTool ?? []} />
              </div>

              <Card className="shadow-none">
                <CardHeader className="p-3 pb-1">
                  <CardTitle>Conversas relevantes</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-2 p-3">
                  {metrics.conversations.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Nenhuma conversa registrada.</p>
                  ) : (
                    metrics.conversations.map((conversation) => (
                      <ConversationRow
                        conversation={conversation}
                        key={conversation.conversationId}
                        onSelect={() => {
                          onSelectConversation(conversation.conversationId);
                          onOpenChange(false);
                        }}
                      />
                    ))
                  )}
                </CardContent>
              </Card>
            </div>
          ) : activeTab === "reviews" ? (
            <ReviewActionsPanel
              onClose={() => onOpenChange(false)}
              onResolveReviewTask={onResolveReviewTask}
              onSelectConversation={onSelectConversation}
              reviewTasks={reviewTasks}
            />
          ) : null}
        </div>
      </section>
    </div>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value
}: {
  icon: LucideIcon;
  label: string;
  value: number | string;
}) {
  return (
    <Card className="shadow-none">
      <CardContent className="flex items-center gap-3 p-3">
        <Icon className="h-4 w-4 text-primary" />
        <div className="min-w-0">
          <p className="text-base font-semibold">{value}</p>
          <p className="truncate text-xs text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function DistributionCard({
  title,
  values
}: {
  title: string;
  values: DashboardDistributionItem[];
}) {
  const max = Math.max(...values.map((value) => value.count), 1);
  return (
    <Card className="shadow-none">
      <CardHeader className="p-3 pb-1">
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-2 p-3 text-xs">
        {values.length === 0 ? (
          <p className="text-muted-foreground">Sem dados.</p>
        ) : (
          values.map((item) => (
            <div className="grid gap-1" key={item.key}>
              <div className="flex items-center justify-between gap-2">
                <span className="min-w-0 truncate font-medium">{item.key}</span>
                <span className="text-muted-foreground">
                  {item.count}
                  {item.averageRunDurationMs ? ` - ${formatDuration(item.averageRunDurationMs)}` : ""}
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary"
                  style={{ width: `${Math.max(6, (item.count / max) * 100)}%` }}
                />
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

function ConversationRow({
  conversation,
  onSelect
}: {
  conversation: DashboardConversationItem;
  onSelect: () => void;
}) {
  return (
    <button
      className="rounded-md border bg-background p-3 text-left transition-colors hover:bg-muted"
      onClick={onSelect}
      type="button"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">
            Conversa {shortId(conversation.conversationId)}
          </p>
          <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
            {conversation.lastMessage ?? "Sem mensagens"}
          </p>
        </div>
        <Badge variant={conversation.reviewPending ? "warning" : "outline"}>
          {conversation.reviewPending ? "revisão" : conversation.status}
        </Badge>
      </div>
      <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
        <span>{conversation.runCount} execuções</span>
        {conversation.latestRunId ? <span>run {shortId(conversation.latestRunId)}</span> : null}
        <span>{formatDate(conversation.updatedAt)}</span>
      </div>
    </button>
  );
}

function ReviewActionsPanel({
  onClose,
  onResolveReviewTask,
  onSelectConversation,
  reviewTasks
}: {
  onClose: () => void;
  onResolveReviewTask: (
    reviewTaskId: string,
    status: "resolved" | "cancelled" | "in_review",
    note: string
  ) => void;
  onSelectConversation: (conversationId: string) => void;
  reviewTasks: ReviewTask[];
}) {
  const [notes, setNotes] = useState<Record<string, string>>({});

  if (reviewTasks.length === 0) {
    return (
      <Card className="shadow-none">
        <CardContent className="p-4 text-sm text-muted-foreground">
          Nenhuma revisão humana pendente.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-3">
      {reviewTasks.map((task) => {
        const note = notes[task.id] ?? "";
        return (
          <Card className="shadow-none" key={task.id}>
            <CardContent className="grid gap-3 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-semibold">{task.reason}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Conversa {shortId(task.conversationId)} - Mensagem {shortId(task.messageId)} -{" "}
                    {formatDate(task.createdAt)}
                  </p>
                </div>
                <Badge variant="warning">{task.status}</Badge>
              </div>
              <textarea
                className="min-h-20 rounded-md border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                onChange={(event) =>
                  setNotes((current) => ({
                    ...current,
                    [task.id]: event.target.value
                  }))
                }
                placeholder="Observação da revisão (opcional)"
                value={note}
              />
              <div className="flex flex-wrap gap-2">
                <Button
                  className="text-xs"
                  onClick={() => onResolveReviewTask(task.id, "resolved", note)}
                  size="sm"
                  type="button"
                >
                  <ClipboardCheck className="h-4 w-4" />
                  Aprovar
                </Button>
                <Button
                  className="text-xs"
                  onClick={() => onResolveReviewTask(task.id, "cancelled", note)}
                  size="sm"
                  type="button"
                  variant="destructive"
                >
                  <ClipboardX className="h-4 w-4" />
                  Rejeitar
                </Button>
                <Button
                  className="border-amber-300 bg-amber-100 text-xs text-amber-950 hover:bg-amber-200"
                  onClick={() => onResolveReviewTask(task.id, "in_review", note)}
                  size="sm"
                  type="button"
                  variant="outline"
                >
                  <Clock3 className="h-4 w-4" />
                  Manter em revisão
                </Button>
                <Button
                  className="text-xs"
                  onClick={() => {
                    onSelectConversation(task.conversationId);
                    onClose();
                  }}
                  size="sm"
                  type="button"
                  variant="outline"
                >
                  <MessageSquare className="h-4 w-4" />
                  Abrir conversa
                </Button>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
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

function asNumber(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("pt-BR", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "2-digit"
  });
}

function shortId(id: string): string {
  return id.slice(0, 8);
}
