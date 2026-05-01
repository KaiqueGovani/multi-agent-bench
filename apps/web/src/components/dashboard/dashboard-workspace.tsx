"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  ClipboardCheck,
  ClipboardX,
  Clock3,
  Database,
  FileText,
  MessageSquare,
  Network,
  ShieldAlert,
  Timer,
  Workflow,
  XCircle,
  type LucideIcon,
} from "lucide-react";

import { RunExecutionPanel } from "@/components/runtime/run-execution-panel";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  getConversation,
  getDashboardMetrics,
  listOpenReviewTasks,
  resolveReviewTask,
} from "@/lib/api/client";
import type {
  ConversationDetailResponse,
  DashboardConversationItem,
  DashboardDistributionItem,
  DashboardMetricsResponse,
  ReviewTask,
} from "@/lib/types";
import { cn } from "@/lib/utils";

export function DashboardWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [metrics, setMetrics] = useState<DashboardMetricsResponse | null>(null);
  const [reviewTasks, setReviewTasks] = useState<ReviewTask[]>([]);
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(
    searchParams.get("conversationId"),
  );
  const [selectedConversation, setSelectedConversation] = useState<ConversationDetailResponse | null>(
    null,
  );
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingConversation, setIsLoadingConversation] = useState(false);

  useEffect(() => {
    setSelectedConversationId(searchParams.get("conversationId"));
  }, [searchParams]);

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
        setSelectedConversationId((current) => current ?? metricsResponse.conversations[0]?.conversationId ?? null);
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

  useEffect(() => {
    if (!selectedConversationId) {
      setSelectedConversation(null);
      setSelectedRunId(null);
      return;
    }

    let cancelled = false;
    setIsLoadingConversation(true);

    void getConversation(selectedConversationId)
      .then((detail) => {
        if (cancelled) {
          return;
        }
        setSelectedConversation(detail);
        setSelectedRunId(detail.runs.at(-1)?.id ?? null);
      })
      .catch((caught) => {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "Falha ao carregar conversa");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingConversation(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedConversationId]);

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
  }

  function selectConversation(conversationId: string) {
    setSelectedConversationId(conversationId);
    router.replace(`/dashboard?conversationId=${conversationId}`, { scroll: false });
  }

  return (
    <main className="min-h-screen bg-background text-foreground" data-testid="dashboard-page">
      <header className="sticky top-0 z-30 border-b bg-background/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" />
              <h1 className="text-lg font-semibold">Dashboard operacional</h1>
              {generatedAt ? <Badge variant="outline">{generatedAt}</Badge> : null}
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Visão operacional das conversas, revisões e execução técnica do runtime.
            </p>
          </div>
          <Link
            className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
            data-testid="dashboard-back-to-chat"
            href={selectedConversationId ? `/?conversationId=${selectedConversationId}` : "/"}
          >
            <ArrowLeft className="h-4 w-4" />
            Voltar ao chat
          </Link>
        </div>
      </header>

      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4">
        {error ? (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
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
            <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
              <MetricCard icon={MessageSquare} label="conversas" value={metrics.totals.conversations} />
              <MetricCard icon={Network} label="runs" value={metrics.totals.runs} />
              <MetricCard icon={CheckCircle2} label="runs concluidos" value={metrics.totals.runsCompleted} />
              <MetricCard icon={ShieldAlert} label="revisoes abertas" value={reviewTasks.length} />
              <MetricCard
                icon={Timer}
                label="latencia media"
                value={formatDuration(metrics.totals.averageRunDurationMs)}
              />
            </section>

            <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
              <div className="grid gap-4">
                <Card className="shadow-none">
                  <CardHeader className="p-4 pb-2">
                    <CardTitle>Conversas em acompanhamento</CardTitle>
                  </CardHeader>
                  <CardContent className="grid gap-3 p-4 pt-0">
                    {metrics.conversations.length === 0 ? (
                      <p className="text-sm text-muted-foreground">Nenhuma conversa registrada.</p>
                    ) : (
                      metrics.conversations.map((conversation) => (
                        <ConversationRow
                          conversation={conversation}
                          isActive={conversation.conversationId === selectedConversationId}
                          key={conversation.conversationId}
                          onOpenChat={() => {
                            router.push(`/?conversationId=${conversation.conversationId}`);
                          }}
                          onSelect={() => selectConversation(conversation.conversationId)}
                        />
                      ))
                    )}
                  </CardContent>
                </Card>

                <div className="grid gap-3 lg:grid-cols-2">
                  <DistributionCard title="Arquiteturas" values={metrics.byArchitecture} />
                  <DistributionCard title="Cenários" values={metrics.byScenario} />
                  <DistributionCard title="Ferramentas" values={metrics.byTool ?? []} />
                  <DistributionCard title="Anexos" values={metrics.byAttachmentType} />
                </div>
              </div>

              <div className="grid gap-4">
                <ReviewQueue
                  onOpenConversation={(conversationId) => selectConversation(conversationId)}
                  onResolveReviewTask={handleResolveReviewTask}
                  reviewTasks={reviewTasks}
                />

                <Card className="shadow-none">
                  <CardHeader className="p-4 pb-2">
                    <CardTitle>Monitor técnico da conversa</CardTitle>
                  </CardHeader>
                  <CardContent className="grid gap-3 p-4 pt-0">
                    {isLoadingConversation ? (
                      <p className="text-sm text-muted-foreground">
                        Carregando detalhes da conversa selecionada...
                      </p>
                    ) : !selectedConversation || selectedConversation.runs.length === 0 ? (
                      <p className="text-sm text-muted-foreground">
                        Selecione uma conversa com execução registrada para inspecionar o runtime.
                      </p>
                    ) : (
                      <>
                        <div className="rounded-xl border bg-card/80 p-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant="outline">
                              conversa {shortId(selectedConversation.conversation.id)}
                            </Badge>
                            <Badge variant="outline">
                              {selectedConversation.runs.length} runs
                            </Badge>
                            <Badge variant="outline">
                              {selectedConversation.reviewTasks.length} revisões
                            </Badge>
                          </div>
                          <p className="mt-2 text-sm text-muted-foreground">
                            Use esta área para acompanhar os detalhes técnicos fora da superfície principal do chat.
                          </p>
                        </div>
                        <RunExecutionPanel
                          onSelectRun={setSelectedRunId}
                          runs={selectedConversation.runs}
                          selectedRunId={selectedRunId}
                          variant="technical"
                        />
                      </>
                    )}
                  </CardContent>
                </Card>
              </div>
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
      <CardContent className="flex items-center gap-3 p-4">
        <div className="rounded-xl bg-primary/10 p-3 text-primary">
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <p className="text-lg font-semibold">{value}</p>
          <p className="truncate text-xs text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function DistributionCard({
  title,
  values,
}: {
  title: string;
  values: DashboardDistributionItem[];
}) {
  const max = Math.max(...values.map((value) => value.count), 1);

  return (
    <Card className="shadow-none">
      <CardHeader className="p-4 pb-2">
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 p-4 pt-0 text-xs">
        {values.length === 0 ? (
          <p className="text-muted-foreground">Sem dados.</p>
        ) : (
          values.map((item) => (
            <div className="grid gap-1.5" key={item.key}>
              <div className="flex items-center justify-between gap-2">
                <span className="min-w-0 truncate font-medium">{item.key}</span>
                <span className="text-muted-foreground">
                  {item.count}
                  {item.averageRunDurationMs ? ` · ${formatDuration(item.averageRunDurationMs)}` : ""}
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary"
                  style={{ width: `${Math.max(10, (item.count / max) * 100)}%` }}
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
  isActive,
  onOpenChat,
  onSelect,
}: {
  conversation: DashboardConversationItem;
  isActive: boolean;
  onOpenChat: () => void;
  onSelect: () => void;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border p-3 transition-colors",
        isActive ? "border-primary bg-primary/5" : "border-border bg-background",
      )}
      data-testid={`dashboard-conversation-${conversation.conversationId}`}
    >
      <button className="w-full text-left" onClick={onSelect} type="button">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">
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
      </button>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
        <span>{conversation.runCount} runs</span>
        {conversation.latestRunId ? <span>run {shortId(conversation.latestRunId)}</span> : null}
        <span>{formatDate(conversation.updatedAt)}</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button onClick={onSelect} size="sm" type="button" variant="outline">
          Inspecionar
        </Button>
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

  return (
    <Card className="shadow-none">
      <CardHeader className="p-4 pb-2">
        <CardTitle>Fila de revisão humana</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 p-4 pt-0">
        {reviewTasks.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhuma revisão aberta no momento.</p>
        ) : (
          reviewTasks.map((task) => {
            const note = notes[task.id] ?? "";
            return (
              <div className="rounded-xl border bg-background p-3" key={task.id}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold">{task.reason}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      conversa {shortId(task.conversationId)} · mensagem {shortId(task.messageId)} · {formatDate(task.createdAt)}
                    </p>
                  </div>
                  <Badge variant="warning">{task.status}</Badge>
                </div>
                <textarea
                  className="mt-3 min-h-20 rounded-md border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  onChange={(event) =>
                    setNotes((current) => ({ ...current, [task.id]: event.target.value }))
                  }
                  placeholder="Observação opcional"
                  value={note}
                />
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button
                    className="text-xs"
                    onClick={() => void onResolveReviewTask(task.id, "resolved", note)}
                    size="sm"
                    type="button"
                  >
                    <ClipboardCheck className="h-4 w-4" />
                    Aprovar
                  </Button>
                  <Button
                    className="text-xs"
                    onClick={() => void onResolveReviewTask(task.id, "cancelled", note)}
                    size="sm"
                    type="button"
                    variant="destructive"
                  >
                    <ClipboardX className="h-4 w-4" />
                    Rejeitar
                  </Button>
                  <Button
                    className="text-xs"
                    onClick={() => void onResolveReviewTask(task.id, "in_review", note)}
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
                    Abrir no monitor
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
  if (!value) {
    return "n/a";
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
