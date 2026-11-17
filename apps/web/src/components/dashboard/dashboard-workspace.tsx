"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useCallback, useRef, useState } from "react";
import {
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  ClipboardCheck,
  ClipboardX,
  Clock3,
  Loader2,
  MessageSquare,
  Network,
  ShieldAlert,
  Timer,
  type LucideIcon,
} from "lucide-react";

import { DistributionBarChart, DistributionPieChart, ArchitectureLatencyChart } from "@/components/common/charts";
import { Badge } from "@/components/ui/badge";
import { formatStatusLabel } from "@/components/runtime/presentation";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  getConversation,
  getDashboardMetrics,
  listOpenReviewTasks,
  resolveReviewTask,
} from "@/lib/api/client";
import type {
  DashboardConversationItem,
  DashboardMetricsResponse,
  Message,
  ReviewTask,
} from "@/lib/types";
import { cn } from "@/lib/utils";

export function DashboardWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [metrics, setMetrics] = useState<DashboardMetricsResponse | null>(null);
  const [reviewTasks, setReviewTasks] = useState<ReviewTask[]>([]);
  const selectedConversationId = searchParams.get("conversationId");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    async function load() {
      try {
        const [metricsResponse, reviewsResponse] = await Promise.all([
          getDashboardMetrics(),
          listOpenReviewTasks(),
        ]);
        if (cancelled) {
          return;
        }
        setMetrics(metricsResponse);
        setReviewTasks(reviewsResponse.reviewTasks);
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "Falha ao carregar dashboard");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const generatedAt = useMemo(() => {
    if (!metrics?.generatedAt) {
      return null;
    }
    return new Date(metrics.generatedAt).toLocaleString("pt-BR", {
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      month: "2-digit",
    });
  }, [metrics?.generatedAt]);

  async function handleResolveReviewTask(
    reviewTaskId: string,
    status: "resolved" | "cancelled" | "in_review",
    note: string,
  ) {
    try {
      setError(null);
      await resolveReviewTask(reviewTaskId, {
        note: note.trim() || undefined,
        resolvedBy: "dashboard_operator",
        status,
      });

      const [metricsResponse, reviewsResponse] = await Promise.all([
        getDashboardMetrics(),
        listOpenReviewTasks(),
      ]);
      setMetrics(metricsResponse);
      setReviewTasks(reviewsResponse.reviewTasks);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Falha ao resolver revisão");
    }
  }

  return (
    <main className="min-h-screen min-w-0 bg-background text-foreground" data-testid="dashboard-page">
      <header className="sticky top-0 z-30 border-b bg-background/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" />
              <h1 className="text-lg font-semibold">Dashboard operacional</h1>
              {generatedAt ? (
                <Badge variant="outline">{generatedAt}</Badge>
              ) : null}
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Conversas, revisões e indicadores de execução em um só lugar.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/research"
              className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
            >
              Resultados da pesquisa
            </Link>
            <Link
            className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
            data-testid="dashboard-back-to-chat"
            href={selectedConversationId ? `/?conversationId=${selectedConversationId}` : "/"}
          >
              <ArrowLeft className="h-4 w-4" />
              Voltar ao chat
            </Link>
          </div>
        </div>
      </header>

      <div className="mx-auto flex min-w-0 max-w-7xl flex-col gap-4 px-3 py-4 sm:px-4">
        {error ? (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive" role="alert">
            {error}
          </div>
        ) : null}

        {isLoading ? (
          <Card className="shadow-none">
            <CardContent className="p-4 text-sm text-muted-foreground">
              Carregando indicadores operacionais...
            </CardContent>
          </Card>
        ) : metrics ? (
          <>
            <section className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
              <MetricCard icon={MessageSquare} label="conversas" value={metrics.totals.conversations} />
              <MetricCard icon={Network} label="execuções" value={metrics.totals.runs} />
              <MetricCard icon={CheckCircle2} label="execuções concluídas" value={metrics.totals.runsCompleted} />
              <MetricCard icon={ShieldAlert} label="revisões abertas" value={reviewTasks.length} />
              <MetricCard
                icon={Timer}
                label="latência média"
                value={formatDuration(metrics.totals.averageRunDurationMs)}
              />
            </section>

            <section aria-label="Indicadores de execução" className="grid min-w-0 grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
              <Card className="min-w-0 shadow-none">
                <CardHeader className="p-4 pb-2">
                  <CardTitle>Comparação entre arquiteturas</CardTitle>
                </CardHeader>
                <CardContent className="grid min-w-0 gap-5 p-4 pt-0 sm:grid-cols-2">
                  <DistributionBarChart data={metrics.byArchitecture} title="Execuções por arquitetura" />
                  <ArchitectureLatencyChart data={metrics.byArchitecture} title="Comparação de latência entre arquiteturas" />
                </CardContent>
              </Card>
              <Card className="min-w-0 shadow-none">
                <CardHeader className="p-4 pb-2">
                  <CardTitle>Uso de ferramentas</CardTitle>
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    Cada chamada é contada uma vez. Roteamento e delegação entre agentes ficam fora desta distribuição.
                  </p>
                </CardHeader>
                <CardContent className="min-w-0 p-4 pt-0">
                  <DistributionPieChart data={metrics.byTool ?? []} title="Chamadas de ferramentas de domínio" />
                </CardContent>
              </Card>
            </section>

            <section className="grid min-w-0 grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
              <Card className="min-w-0 shadow-none">
                <CardHeader className="p-4 pb-2">
                  <CardTitle>Conversas em acompanhamento</CardTitle>
                </CardHeader>
                <CardContent className="grid min-w-0 grid-cols-1 gap-3 p-4 pt-0">
                  {metrics.conversations.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Nenhuma conversa registrada.</p>
                  ) : metrics.conversations.map((conversation) => (
                    <ConversationRow
                      conversation={conversation}
                      key={conversation.conversationId}
                      onOpenChat={() => router.push(`/?conversationId=${conversation.conversationId}`)}
                    />
                  ))}
                </CardContent>
              </Card>
              <ReviewQueue
                onOpenConversation={(conversationId) => router.push(`/?conversationId=${conversationId}`)}
                onResolveReviewTask={handleResolveReviewTask}
                reviewTasks={reviewTasks}
              />
            </section>
          </>
        ) : null}
      </div>
    </main>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: number | string;
}) {
  return (
    <Card className="shadow-none">
      <CardContent className="flex items-center gap-2 p-3 sm:gap-3 sm:p-4">
        <div className="shrink-0 rounded-xl bg-primary/10 p-2 text-primary sm:p-3">
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <p className="text-lg font-semibold">{value}</p>
          <p className="text-xs leading-relaxed text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function ConversationRow({
  conversation,
  onOpenChat,
}: {
  conversation: DashboardConversationItem;
  onOpenChat: () => void;
}) {
  return (
    <div
      className="min-w-0 rounded-xl border bg-background p-3"
      data-testid={`dashboard-conversation-${conversation.conversationId}`}
    >
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">
              {conversation.title || `Conversa ${shortId(conversation.conversationId)}`}
            </p>
            <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
              {conversation.lastMessage ?? "Sem mensagens"}
            </p>
          </div>
          <Badge variant={conversation.reviewPending ? "warning" : "outline"}>
            {conversation.reviewPending ? "Revisão" : conversation.status === "active" ? "Ativa" : formatStatusLabel(conversation.status)}
          </Badge>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
        <span>{conversation.runCount} execuções</span>
        {conversation.latestRunId ? (
          <span>run {shortId(conversation.latestRunId)}</span>
        ) : null}
        <span>{formatDate(conversation.updatedAt)}</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button onClick={onOpenChat} size="sm" type="button">
          Abrir chat
        </Button>
      </div>
    </div>
  );
}

function ReviewQueue({
  onOpenConversation,
  onResolveReviewTask,
  reviewTasks,
}: {
  onOpenConversation: (conversationId: string) => void;
  onResolveReviewTask: (
    reviewTaskId: string,
    status: "resolved" | "cancelled" | "in_review",
    note: string,
  ) => Promise<void>;
  reviewTasks: ReviewTask[];
}) {
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [pending, setPending] = useState<Record<string, boolean>>({});
  const pendingRef = useRef(new Set<string>());
  async function resolve(id: string, status: "resolved" | "cancelled" | "in_review", note: string) {
    if (pendingRef.current.has(id)) return;
    pendingRef.current.add(id);
    setPending(current => ({ ...current, [id]: true }));
    try { await onResolveReviewTask(id, status, note); }
    finally { pendingRef.current.delete(id); setPending(current => ({ ...current, [id]: false })); }
  }
  const excerptCacheRef = useRef(new Map<string, Message[]>());
  const [excerpts, setExcerpts] = useState<Record<string, Message[] | "loading" | "error">>({});

  const loadExcerpt = useCallback((conversationId: string) => {
    if (excerptCacheRef.current.has(conversationId)) {
      setExcerpts((prev) => ({ ...prev, [conversationId]: excerptCacheRef.current.get(conversationId)! }));
      return;
    }
    setExcerpts((prev) => prev[conversationId] ? prev : { ...prev, [conversationId]: "loading" });
    getConversation(conversationId)
      .then((detail) => {
        const lastTwo = detail.messages.slice(-2);
        excerptCacheRef.current.set(conversationId, lastTwo);
        setExcerpts((prev) => ({ ...prev, [conversationId]: lastTwo }));
      })
      .catch(() => {
        setExcerpts((prev) => ({ ...prev, [conversationId]: "error" }));
      });
  }, []);

  useEffect(() => {
    for (const task of reviewTasks) {
      loadExcerpt(task.conversationId);
    }
  }, [reviewTasks, loadExcerpt]);

  return (
    <Card className="shadow-none">
      <CardHeader className="p-4 pb-2">
        <CardTitle>Fila de revisão humana</CardTitle>
      </CardHeader>
      <CardContent className="grid min-w-0 grid-cols-1 gap-3 p-4 pt-0">
        {reviewTasks.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Nenhuma revisão aberta no momento.
          </p>
        ) : (
          reviewTasks.map((task) => {
            const note = notes[task.id] ?? "";
            const excerpt = excerpts[task.conversationId];
            return (
              <div className="rounded-xl border bg-background p-3" key={task.id}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="break-words text-sm font-semibold">{formatReviewReason(task.reason)}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      conversa {shortId(task.conversationId)} · mensagem{" "}
                      {shortId(task.messageId)} · {formatDate(task.createdAt)}
                    </p>
                  </div>
                  <Badge variant="warning">{task.status === "open" ? "Aberta" : task.status === "in_review" ? "Em revisão" : formatStatusLabel(task.status)}</Badge>
                </div>
                <div className="mt-2 space-y-0.5">
                  {excerpt === "loading" ? (
                    <p className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Loader2 className="h-3 w-3 animate-spin" />
                    </p>
                  ) : excerpt === "error" ? (
                    <p className="truncate text-xs text-muted-foreground">
                      Sem contexto disponível
                    </p>
                  ) : Array.isArray(excerpt) ? (
                    excerpt.map((m) => (
                      <p className="truncate text-xs text-muted-foreground" key={m.id}>
                        {m.direction === "inbound" ? "Cliente" : "Assistente"}: {m.contentText?.slice(0, 120)}
                      </p>
                    ))
                  ) : null}
                </div>
                <textarea
                  aria-label={`Observação da revisão ${task.id}`}
                  className="mt-3 min-h-20 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  onChange={(event) =>
                    setNotes((current) => ({ ...current, [task.id]: event.target.value }))
                  }
                  placeholder="Observação opcional"
                  value={note}
                />
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button
                    className="text-xs"
                    disabled={pending[task.id]}
                    onClick={() =>
                      void resolve(task.id, "resolved", note)
                    }
                    size="sm"
                    type="button"
                  >
                    <ClipboardCheck className="h-4 w-4" />
                    Aprovar
                  </Button>
                  <Button
                    className="text-xs"
                    disabled={pending[task.id]}
                    onClick={() =>
                      void resolve(task.id, "cancelled", note)
                    }
                    size="sm"
                    type="button"
                    variant="destructive"
                  >
                    <ClipboardX className="h-4 w-4" />
                    Rejeitar
                  </Button>
                  <Button
                    className="text-xs"
                    disabled={pending[task.id]}
                    onClick={() =>
                      void resolve(task.id, "in_review", note)
                    }
                    size="sm"
                    type="button"
                    variant="outline"
                  >
                    <Clock3 className="h-4 w-4" />
                    Manter em revisão
                  </Button>
                  <Button
                    className="text-xs"
                    onClick={() => onOpenConversation(task.conversationId)}
                    size="sm"
                    type="button"
                    variant="outline"
                  >
                    <MessageSquare className="h-4 w-4" />
                    Abrir conversa
                  </Button>
                </div>
              </div>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}

function formatDuration(value: number | null | undefined): string {
  if (value == null) {
    return "Sem medição";
  }
  if (value < 1000) {
    return `${value} ms`;
  }
  return `${(value / 1000).toFixed(1)} s`;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("pt-BR", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "2-digit",
  });
}

function shortId(id: string): string {
  return id.slice(0, 8);
}


function formatReviewReason(reason: string): string {
  return ({ validacao_clinica: "Validação clínica", clinical_guidance: "Orientação clínica" } as Record<string, string>)[reason] ?? reason.replaceAll("_", " ");
}
