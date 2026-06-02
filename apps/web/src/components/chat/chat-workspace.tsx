"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bot,
  ChevronDown,
  CheckCircle2,
  Clock3,
  Globe2,
  Info,
  MessageSquare,
  Network,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Loader2,
  Search,
  Workflow,
  X
} from "lucide-react";

import { EventTimeline } from "@/components/events/event-timeline";
import { ConversationInspector } from "@/components/inspection/conversation-inspector";
import { CentralizedFlow, SwarmFlow, WorkflowFlow } from "@/components/runtime/architecture-flow";
import { ArchitectureComparisonOverview } from "@/components/runtime/architecture-comparison-overview";
import { formatArchitectureLabel as formatArchitectureLabelText } from "@/components/runtime/presentation";
import { RunExecutionPanel } from "@/components/runtime/run-execution-panel";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useConversation } from "@/hooks/use-conversation";
import { getHealth, getRunExecution } from "@/lib/api/client";
import type { ArchitectureMode, ConversationSummary, ExecutionMode, Message, ReviewTask, ReviewTaskStatus, Run, RunExecutionEvent, RunExecutionResponse, RuntimeHealthStatus } from "@/lib/types";
import { cn } from "@/lib/utils";
import { MessageComposer } from "./message-composer";
import { MessageList } from "./message-list";

type WorkspaceTab = "conversa" | "visao-geral" | "atividade";

const workspaceTabs: Array<{ key: WorkspaceTab; label: string }> = [
  { key: "conversa", label: "Conversa" },
  { key: "visao-geral", label: "Visão Geral" },
  { key: "atividade", label: "Atividade" },
];

const architectureOptions: Array<{ label: string; value: ArchitectureMode }> = [
  { label: "Todas as arquiteturas", value: "all_architectures" },
  { label: "Orquestração centralizada", value: "centralized_orchestration" },
  { label: "Workflow estruturado", value: "structured_workflow" },
  { label: "Swarm descentralizado", value: "decentralized_swarm" }
];

export function ChatWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);
  const [isDraftConversation, setIsDraftConversation] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedFlowRunId, setSelectedFlowRunId] = useState<string | null>(null);
  const [selectedFlowExecution, setSelectedFlowExecution] = useState<RunExecutionResponse | null>(null);
  const [architectureMode, setArchitectureMode] = useState<ArchitectureMode>(
    "all_architectures"
  );
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("real");
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeHealthStatus | null>(null);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("conversa");
  const [isFlowOpen, setIsFlowOpen] = useState<boolean>(() => typeof window !== "undefined" && window.localStorage.getItem("chat-flow-open") === "true");
  const [dismissedError, setDismissedError] = useState<string | null>(null);
  const {
    attachments,
    attachmentsByMessage,
    connectionStatus,
    conversation,
    conversationId,
    conversationSummaries,
    error,
    events,
    isCreatingConversation,
    isLoadingConversation,
    isSending,
    messages,
    openReviewTasks,
    reviewTasks,
    runExecution,
    runs,
    sendMessage,
    selectConversation,
    startConversation,
    updateReviewTask
  } = useConversation(architectureMode, executionMode);
  const layoutColumns = activeTab === "conversa"
    ? getLayoutColumns(isHistoryOpen)
    : "lg:grid-cols-1";
  const requestedConversationId = searchParams.get("conversationId");
  const hasActiveConversation = Boolean(conversationId);
  const flowRuns = buildLatestArchitectureRuns(runs);
  const isMultiArchitecture = flowRuns.length > 1;
  const selectedRun = flowRuns.find((r) => r.id === selectedFlowRunId) ?? null;
  const selectedArchitectureKey = selectedRun ? readArchitectureKey(selectedRun) : null;
  const displayedFlowExecution = pickDisplayedExecution({
    selectedFlowRunId,
    selectedFlowExecution,
    runExecution,
    isMultiArchitecture,
  });
  const filteredMessages = filterMessagesForArchitecture({
    messages,
    runs,
    isMultiArchitecture,
    selectedArchitectureKey,
    selectedFlowRunId,
  });

  function handleStartDraftConversation() {
    setIsDraftConversation(true);
    router.replace("/", { scroll: false });
    setIsInspectorOpen(false);
    setSelectedRunId(null);
    setSelectedFlowRunId(null);
    setSelectedFlowExecution(null);
    void startConversation();
  }

  useEffect(() => {
    localStorage.setItem("chat-flow-open", String(isFlowOpen));
  }, [isFlowOpen]);

  useEffect(() => {
    let cancelled = false;
    async function refreshRuntimeStatus() {
      try {
        const health = await getHealth();
        if (!cancelled) {
          setRuntimeStatus(health.runtime);
        }
      } catch {
        if (!cancelled) {
          setRuntimeStatus({
            mode: executionMode,
            reachable: false,
            ready: false,
            llm: null,
            error: "API indisponivel",
          });
        }
      }
    }
    void refreshRuntimeStatus();
    const intervalId = window.setInterval(refreshRuntimeStatus, 15000);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [executionMode]);

  useEffect(() => {
    if (!runs.length) {
      setSelectedRunId(null);
      return;
    }
    setSelectedRunId((current) => current ?? runs[runs.length - 1].id);
  }, [runs]);

  useEffect(() => {
    if (flowRuns.length === 0) {
      setSelectedFlowRunId(null);
      setSelectedFlowExecution(null);
      return;
    }
    setSelectedFlowRunId((current) => {
      if (current && flowRuns.some((run) => run.id === current)) {
        return current;
      }
      return flowRuns[0].id;
    });
  }, [flowRuns]);

  useEffect(() => {
    if (!selectedFlowRunId) {
      setSelectedFlowExecution(null);
      return;
    }
    if (runExecution?.run.id === selectedFlowRunId) {
      setSelectedFlowExecution(null);
      return;
    }

    let cancelled = false;
    void getRunExecution(selectedFlowRunId)
      .then((execution) => {
        if (!cancelled) {
          setSelectedFlowExecution(execution);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSelectedFlowExecution(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [runExecution?.run.id, selectedFlowRunId]);

  useEffect(() => {
    if (isDraftConversation || !requestedConversationId || requestedConversationId === conversationId) {
      return;
    }
    void selectConversation(requestedConversationId);
  }, [conversationId, isDraftConversation, requestedConversationId, selectConversation]);

  useEffect(() => {
    if (!conversationId || requestedConversationId === conversationId) {
      return;
    }
    if (!isDraftConversation && requestedConversationId) {
      return;
    }
    setIsDraftConversation(false);
    router.replace(`/?conversationId=${conversationId}`, { scroll: false });
  }, [conversationId, isDraftConversation, requestedConversationId, router]);

  return (
    <main
      className={`grid min-h-screen grid-cols-1 overflow-x-hidden bg-background text-foreground lg:h-screen lg:overflow-hidden ${layoutColumns}`}
    >
      {activeTab === "conversa" ? (
        <ConversationHistory
          activeConversationId={conversationId}
          conversations={conversationSummaries}
          isOpen={isHistoryOpen}
          isCreatingConversation={isCreatingConversation}
          isLoadingConversation={isLoadingConversation}
          openReviewCount={openReviewTasks.length}
          onCreateConversation={handleStartDraftConversation}
          onOpenChange={setIsHistoryOpen}
          onSelectConversation={(summary) => {
            if (summary.conversationId === conversationId) {
              return;
            }
            router.replace(`/?conversationId=${summary.conversationId}`, { scroll: false });
            setIsDraftConversation(false);
            if (isArchitectureMode(summary.architectureMode)) {
              setArchitectureMode(summary.architectureMode);
            }
            if (typeof window !== "undefined" && window.innerWidth < 1024) {
              setIsHistoryOpen(false);
            }
          }}
        />
      ) : null}

      <section className="flex min-w-0 flex-col overflow-hidden">
        <header className="flex min-h-16 items-center gap-3 border-b bg-card px-3 py-2 shadow-sm sm:px-4">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <Button
              className="shrink-0 lg:hidden"
              data-testid="history-toggle"
              onClick={() => setIsHistoryOpen((current) => !current)}
              size="icon"
              type="button"
              variant="outline"
            >
              {isHistoryOpen ? (
                <PanelLeftClose className="h-4 w-4" />
              ) : (
                <PanelLeftOpen className="h-4 w-4" />
              )}
            </Button>
            <div className="min-w-0 flex-1">
              <div className="flex min-w-0 items-center gap-2">
                <h1 className="truncate text-base font-semibold">
                  Atendimento farmacêutico POC
                </h1>
              {conversationId ? (
                <Badge variant="outline">{formatArchitectureLabel(architectureMode)}</Badge>
              ) : null}
                <HeaderContextTooltip
                  architectureMode={architectureMode}
                  executionMode={executionMode}
                  runtimeStatus={runtimeStatus}
                />
              </div>
              <p className="truncate text-xs text-muted-foreground">
                {conversationId ? `Conversa ${conversationId}` : "Nenhuma conversa ativa"}
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button
              aria-label={isFlowOpen ? "Esconder fluxo" : "Mostrar fluxo"}
              aria-pressed={isFlowOpen}
              data-testid="flow-toggle"
              onClick={() => setIsFlowOpen((v) => !v)}
              size="icon"
              type="button"
              variant={isFlowOpen ? "secondary" : "outline"}
            >
              <Workflow className="h-4 w-4" />
            </Button>
            <Button
              disabled={!hasActiveConversation}
              onClick={() => setIsInspectorOpen(true)}
              size="sm"
              type="button"
              variant="outline"
            >
              <Search className="h-4 w-4" />
              <span className="hidden sm:inline">Inspeção</span>
            </Button>
            <ExecutionModeToggle
              executionMode={executionMode}
              onExecutionModeChange={setExecutionMode}
              runtimeStatus={runtimeStatus}
            />
            {openReviewTasks.length > 0 ? (
              <Link
                aria-label={`Ver ${openReviewTasks.length} revisões abertas`}
                className={cn(buttonVariants({ size: "sm", variant: "outline" }), "gap-1.5")}
                data-testid="review-badge-link"
                href="/dashboard"
              >
                <AlertTriangle className="h-4 w-4 text-amber-600" />
                <span className="hidden sm:inline">Revisões</span>
                <Badge aria-live="polite" variant="warning">
                  {openReviewTasks.length}
                </Badge>
              </Link>
            ) : null}
            <Link
              className={cn(buttonVariants({ size: "sm", variant: "outline" }))}
              data-testid="dashboard-link"
              href={conversationId ? `/dashboard?conversationId=${conversationId}` : "/dashboard"}
            >
              <BarChart3 className="h-4 w-4" />
              <span className="hidden sm:inline">Dashboard</span>
            </Link>
            <Button
              disabled={isCreatingConversation}
              onClick={handleStartDraftConversation}
              size="sm"
              type="button"
            >
              {isCreatingConversation ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="hidden sm:inline">Criando</span>
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4" />
                  <span className="hidden sm:inline">Nova conversa</span>
                </>
              )}
            </Button>
          </div>
        </header>

        {/* Workspace tab bar */}
        <nav className="flex items-center gap-1 border-b bg-card/80 px-3 py-1.5">
          {workspaceTabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {error && error !== dismissedError ? (
          <Alert className="rounded-none border-x-0 border-t-0 px-5 py-2" variant="destructive">
            <AlertDescription className="flex items-center justify-between gap-2">
              <span>{error}</span>
              <button
                aria-label="Fechar erro"
                className="shrink-0 rounded-sm p-0.5 hover:bg-destructive/20"
                onClick={() => setDismissedError(error)}
                type="button"
              >
                <X className="h-4 w-4" />
              </button>
            </AlertDescription>
          </Alert>
        ) : null}

        <ConversationInspector
          attachments={attachments}
          conversation={conversation}
          events={events}
          isOpen={isInspectorOpen}
          messages={messages}
          onOpenChange={setIsInspectorOpen}
          reviewTasks={reviewTasks}
          runs={runs}
        />

        {/* Tab content — flex-1 + overflow-hidden ensures the parent fills remaining space */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {activeTab === "conversa" ? (
            <>
              <div className="flex flex-1 flex-col overflow-hidden bg-background">
                {isMultiArchitecture ? (
                  <div className="flex items-center gap-2 border-b bg-card/60 px-3 py-2">
                    <span className="text-xs text-muted-foreground">Arquitetura:</span>
                    <ArchitectureFlowPicker
                      runs={flowRuns}
                      selectedRunId={selectedFlowRunId}
                      onSelectRun={setSelectedFlowRunId}
                    />
                  </div>
                ) : null}
                {isFlowOpen ? (
                  displayedFlowExecution?.projection ? (
                    <div
                      aria-label="Fluxo da arquitetura"
                      className="shrink-0 border-b bg-muted/30 p-2"
                      data-testid="chat-flow-panel"
                      style={{ minHeight: 260, maxHeight: 360, overflow: "auto" }}
                    >
                      <ChatRuntimeVisual
                        architectureMode={
                          isArchitectureMode(displayedFlowExecution.projection.architectureMode)
                            ? displayedFlowExecution.projection.architectureMode
                            : architectureMode
                        }
                        projection={displayedFlowExecution.projection}
                        runStatus={displayedFlowExecution.projection.runStatus}
                        executionEvents={displayedFlowExecution.executionEvents ?? []}
                      />
                    </div>
                  ) : (
                    <div
                      className="shrink-0 border-b bg-muted/30 p-6 text-center text-sm text-muted-foreground"
                      data-testid="chat-flow-panel"
                    >
                      Envie uma mensagem para visualizar o fluxo.
                    </div>
                  )
                ) : null}
                <div className="flex-1 overflow-y-auto">
                  <MessageList
                    attachmentsByMessage={attachmentsByMessage}
                    isLoading={isLoadingConversation}
                    messages={filteredMessages}
                  />
                </div>
              </div>
              <MessageComposer
                architectureMode={architectureMode}
                disabled={false}
                isArchitectureLocked={hasActiveConversation}
                isSending={isSending}
                onArchitectureModeChange={setArchitectureMode}
                onSend={sendMessage}
              />
            </>
          ) : null}

          {activeTab === "visao-geral" ? (
            <div className="flex-1 overflow-y-auto bg-background p-4">
              {runs.length > 0 ? (
                <div className="grid gap-4">
                  {hasArchitectureComparison(runs, architectureMode) ? (
                    <ArchitectureComparisonOverview runs={runs} />
                  ) : (
                    <RunExecutionPanel
                      hideTabs
                      onSelectRun={setSelectedRunId}
                      runs={runs}
                      selectedRunId={selectedRunId}
                      variant="technical"
                    />
                  )}
                </div>
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                  Nenhuma run ativa para exibir.
                </div>
              )}
            </div>
          ) : null}

          {activeTab === "atividade" ? (
            <div className="flex-1 overflow-y-auto bg-background">
              <EventTimeline
                architectureMode={architectureMode}
                connectionStatus={connectionStatus}
                events={events}
                isOpen={true}
                onOpenChange={() => {}}
                reviewPanel={
                  <ReviewPanel onResolve={updateReviewTask} reviewTasks={reviewTasks} />
                }
              />
            </div>
          ) : null}
        </div>
      </section>

    </main>
  );
}

function ConversationHistory({
  activeConversationId,
  conversations,
  isOpen,
  isCreatingConversation,
  isLoadingConversation,
  openReviewCount,
  onCreateConversation,
  onOpenChange,
  onSelectConversation
}: {
  activeConversationId: string | null;
  conversations: ConversationSummary[];
  isOpen: boolean;
  isCreatingConversation: boolean;
  isLoadingConversation: boolean;
  openReviewCount: number;
  onCreateConversation: () => void;
  onOpenChange: (open: boolean) => void;
  onSelectConversation: (summary: ConversationSummary) => void;
}) {
  return (
    <aside
      className={`border-b bg-card lg:flex lg:min-h-0 lg:flex-col lg:border-b-0 lg:border-r ${
        isOpen ? "flex min-h-[220px] flex-col" : "hidden lg:flex"
      }`}
    >
      <div className="flex items-center justify-between gap-2 border-b px-3 py-3">
        {isOpen ? (
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold">Conversas</h2>
            <p className="truncate text-xs text-muted-foreground">
              {conversations.length} recentes
              {openReviewCount > 0 ? ` - ${openReviewCount} revisões abertas` : ""}
            </p>
          </div>
        ) : null}
        <div className="flex items-center gap-2">
          {isOpen ? (
            <Button
              disabled={isCreatingConversation}
              onClick={onCreateConversation}
              size="icon"
              type="button"
              variant="outline"
            >
              {isCreatingConversation ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
            </Button>
          ) : null}
          <button
            className="hidden h-8 w-8 items-center justify-center rounded-md border text-muted-foreground transition-colors hover:bg-muted hover:text-foreground lg:inline-flex"
            onClick={() => onOpenChange(!isOpen)}
            type="button"
          >
            {isOpen ? (
              <PanelLeftClose className="h-4 w-4" />
            ) : (
              <PanelLeftOpen className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>
      {!isOpen ? (
        <button
          className="hidden flex-1 items-center justify-start gap-3 px-4 py-4 text-muted-foreground [writing-mode:vertical-rl] hover:bg-muted hover:text-foreground lg:flex"
          onClick={() => onOpenChange(true)}
          type="button"
        >
          <span className="text-xs font-medium">Conversas</span>
          {conversations.length > 0 ? (
            <Badge className="[writing-mode:horizontal-tb]">{conversations.length}</Badge>
          ) : null}
        </button>
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto p-2">
          {conversations.length === 0 ? (
            <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
              Nenhuma conversa registrada.
            </div>
          ) : (
            <ol className="space-y-2">
              {conversations.map((summary) => {
                const isActive = summary.conversationId === activeConversationId;

                return (
                  <li key={summary.conversationId}>
                    <button
                      className={`w-full rounded-md border p-3 text-left transition-colors ${
                        isActive
                          ? "border-primary bg-primary/10"
                          : "border-border hover:bg-muted"
                      }`}
                      data-testid={`conversation-row-${summary.conversationId}`}
                      onClick={() => onSelectConversation(summary)}
                      type="button"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex min-w-0 items-center gap-2">
                          <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
                          <span className="truncate text-sm font-medium">
                            {shortId(summary.conversationId)}
                          </span>
                        </div>
                        <Badge
                          className="gap-1"
                          variant={summary.reviewPending ? "warning" : statusVariant(summary.status)}
                        >
                          <ConversationStatusIcon
                            reviewPending={summary.reviewPending}
                            status={summary.status}
                          />
                          {summary.reviewPending ? "revisão" : summary.status}
                        </Badge>
                      </div>
                      <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">
                        {formatConversationPreview(summary.lastMessage)}
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                        <span>{summary.messageCount} msg</span>
                        <span>{summary.eventCount} evt</span>
                        {summary.latestRunId ? (
                          <span>run {shortId(summary.latestRunId)}</span>
                        ) : null}
                        <span>{formatUpdatedAt(summary.updatedAt)}</span>
                      </div>
                      {isActive && isLoadingConversation ? (
                        <div className="mt-2 flex items-center gap-1 text-[11px] text-muted-foreground">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          Carregando conversa
                        </div>
                      ) : null}
                    </button>
                  </li>
                );
              })}
            </ol>
          )}
        </div>
      )}
    </aside>
  );
}

function ReviewPanel({
  onResolve,
  reviewTasks
}: {
  onResolve?: (id: string, status: Extract<ReviewTaskStatus, "resolved" | "cancelled" | "in_review">, note?: string) => Promise<void>;
  reviewTasks: ReviewTask[];
}) {
  const openTasks = reviewTasks.filter(
    (task) => task.status === "open" || task.status === "in_review"
  );
  const hasOpenTasks = openTasks.length > 0;
  const [isExpanded, setIsExpanded] = useState(hasOpenTasks);
  const [pending, setPending] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  if (reviewTasks.length === 0) {
    return null;
  }

  async function handleResolve(taskId: string, status: Extract<ReviewTaskStatus, "resolved" | "cancelled" | "in_review">) {
    if (!onResolve) return;
    setPending(taskId);
    setErrors((prev) => {
      const next = { ...prev };
      delete next[taskId];
      return next;
    });
    try {
      await onResolve(taskId, status, notes[taskId]);
    } catch (caught) {
      const message =
        caught instanceof Error &&
        (caught.message.includes("409") || caught.message.includes("404"))
          ? "Esta revisão já foi resolvida por outro usuário."
          : "Erro ao resolver revisão. Tente novamente.";
      setErrors((prev) => ({ ...prev, [taskId]: message }));
    } finally {
      setPending(null);
    }
  }

  return (
    <div className={hasOpenTasks ? "bg-amber-50/80 p-3" : "bg-muted/30 p-3"}>
      <div
        className={`flex items-start justify-between gap-3 rounded-md border p-3 ${
          hasOpenTasks
            ? "border-amber-200 bg-amber-100/80"
            : "border-border bg-background"
        }`}
      >
        <button
          className="min-w-0 flex-1 text-left"
          onClick={() => setIsExpanded((current) => !current)}
          type="button"
        >
          <div className="flex items-center gap-2">
            {hasOpenTasks ? (
              <AlertTriangle className="h-4 w-4 text-amber-700" />
            ) : (
              <CheckCircle2 className="h-4 w-4 text-primary" />
            )}
            <h3 className="text-sm font-semibold">
              {hasOpenTasks ? "Ação humana necessária" : "Revisão humana concluída"}
            </h3>
          </div>
          <p
            className={`mt-1 text-xs ${
              hasOpenTasks ? "text-amber-900" : "text-muted-foreground"
            }`}
          >
            {hasOpenTasks
              ? "Revise a solicitação e escolha uma decisão rápida. A observação é opcional."
              : "Não há pendências humanas abertas nesta conversa."}
          </p>
        </button>
        <div className="flex shrink-0 items-center gap-2">
          <Badge variant={hasOpenTasks ? "warning" : "success"}>
            {hasOpenTasks ? `${openTasks.length} pendente` : "sem pendências"}
          </Badge>
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
      <div className="mt-3 space-y-3">
        {reviewTasks.map((task) => {
          const isOpen = task.status === "open" || task.status === "in_review";
          const isPending = pending === task.id;
          const taskError = errors[task.id];

          return (
            <div className="rounded-md border bg-background p-3" key={task.id}>
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-xs font-medium" id={`${task.id}-reason`}>{task.reason}</p>
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    Mensagem {shortId(task.messageId)} - {formatUpdatedAt(task.createdAt)}
                  </p>
                </div>
                <Badge variant={isOpen ? "warning" : "success"}>{task.status}</Badge>
              </div>
              {isOpen && onResolve ? (
                <div className="mt-2 space-y-2">
                  <Textarea
                    aria-describedby={`${task.id}-reason`}
                    aria-label="Nota da revisão"
                    className="min-h-16 text-xs"
                    onChange={(e) =>
                      setNotes((prev) => ({ ...prev, [task.id]: e.target.value }))
                    }
                    placeholder="Observação opcional"
                    value={notes[task.id] ?? ""}
                  />
                  {taskError ? (
                    <p className="text-xs text-destructive">{taskError}</p>
                  ) : null}
                  <div className="flex flex-wrap gap-2">
                    <Button
                      aria-label="Aprovar"
                      className="text-xs"
                      data-testid={`review-approve-${task.id}`}
                      disabled={isPending}
                      onClick={() => void handleResolve(task.id, "resolved")}
                      size="sm"
                      type="button"
                    >
                      Aprovar
                    </Button>
                    <Button
                      aria-label="Rejeitar"
                      className="text-xs"
                      data-testid={`review-reject-${task.id}`}
                      disabled={isPending}
                      onClick={() => void handleResolve(task.id, "cancelled")}
                      size="sm"
                      type="button"
                      variant="destructive"
                    >
                      Rejeitar
                    </Button>
                    <Button
                      aria-label="Manter em revisão"
                      className="text-xs"
                      data-testid={`review-keep-${task.id}`}
                      disabled={isPending}
                      onClick={() => void handleResolve(task.id, "in_review")}
                      size="sm"
                      type="button"
                      variant="outline"
                    >
                      Manter em revisão
                    </Button>
                  </div>
                </div>
              ) : isOpen ? (
                <p className="mt-2 text-[11px] text-amber-800">
                  Um profissional está avaliando a resposta.
                </p>
              ) : task.resolvedAt ? (
                <p className="mt-2 text-[11px] text-muted-foreground">
                  Resolvida em {formatUpdatedAt(task.resolvedAt)}
                </p>
              ) : null}
            </div>
          );
        })}
      </div>
      ) : null}
    </div>
  );
}

function ExecutionModeToggle({
  executionMode,
  onExecutionModeChange,
  runtimeStatus
}: {
  executionMode: ExecutionMode;
  onExecutionModeChange: (mode: ExecutionMode) => void;
  runtimeStatus: RuntimeHealthStatus | null;
}) {
  const isMock = executionMode === "mock";
  const isChecking = !isMock && !runtimeStatus;
  const isReady = !isMock && Boolean(runtimeStatus?.ready);
  const label = isMock ? "Simulado" : isChecking ? "Verificando" : isReady ? "LLM ativo" : "LLM off";
  return (
    <button
      aria-label={`Modo de execução: ${label}`}
      className="flex h-9 items-center gap-2 rounded-md border bg-background px-3 text-sm transition-colors hover:bg-muted"
      onClick={() => onExecutionModeChange(isMock ? "real" : "mock")}
      type="button"
    >
      <span
        className={`inline-block h-2 w-2 rounded-full ${
          isMock ? "bg-amber-400" : isChecking ? "bg-sky-500" : isReady ? "bg-emerald-500" : "bg-red-500"
        }`}
      />
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}

function HeaderContextTooltip({
  architectureMode,
  executionMode,
  runtimeStatus
}: {
  architectureMode: ArchitectureMode;
  executionMode: ExecutionMode;
  runtimeStatus: RuntimeHealthStatus | null;
}) {
  const llm = runtimeStatus?.llm;
  return (
    <div className="group relative hidden shrink-0 sm:block">
      <button
        aria-label="Metadados da conversa"
        className="flex h-7 items-center gap-1 rounded-md border bg-background px-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        type="button"
      >
        <Info className="h-3.5 w-3.5" />
        <Globe2 className="h-3.5 w-3.5" />
        <Bot className="h-3.5 w-3.5" />
        <ArchitectureIcon mode={architectureMode} />
      </button>
      <div className="pointer-events-none absolute left-0 top-9 z-40 hidden w-72 rounded-md border bg-card p-3 text-xs text-card-foreground shadow-lg group-hover:block group-focus-within:block">
        <div className="grid gap-2">
          <p className="font-medium">Contexto da conversa</p>
          <div className="grid gap-1 text-muted-foreground">
            <p>Plataforma: web chat</p>
            <p>Runtime: {executionMode === "real" ? "agent runtime" : "mock runtime"}</p>
            <p>LLM: {formatRuntimeStatus(runtimeStatus)}</p>
            {llm ? <p>Modelo: {llm.modelId}</p> : null}
            {runtimeStatus?.error ? <p>Erro: {runtimeStatus.error}</p> : null}
            <p>Arquitetura: {formatArchitectureMode(architectureMode)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function formatRuntimeStatus(status: RuntimeHealthStatus | null): string {
  if (!status) {
    return "verificando";
  }
  if (status.ready) {
    return "ativo, token configurado";
  }
  if (!status.reachable) {
    return "runtime indisponivel";
  }
  if (status.llm && !status.llm.tokenConfigured) {
    return "token ausente";
  }
  if (status.llm && !status.llm.enabled) {
    return "live LLM desligado";
  }
  return "nao pronto";
}

function formatArchitectureMode(mode: ArchitectureMode): string {
  return formatArchitectureLabelText(mode);
}

function ArchitectureFlowPicker({
  runs,
  selectedRunId,
  onSelectRun,
}: {
  runs: Run[];
  selectedRunId: string | null;
  onSelectRun: (runId: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {runs.map((run) => {
        const architecture = readArchitectureKey(run);
        const selected = run.id === selectedRunId;
        return (
          <button
            className={cn(
              "inline-flex h-8 items-center gap-2 rounded-md border px-3 text-xs font-medium transition-colors",
              selected
                ? "border-primary bg-primary/10 text-foreground"
                : "border-border bg-background text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
            key={run.id}
            onClick={() => onSelectRun(run.id)}
            type="button"
          >
            <ArchitectureIcon mode={architecture} />
            <span>{formatArchitectureLabel(architecture)}</span>
            <span className="text-[11px] text-muted-foreground">run {shortId(run.id)}</span>
          </button>
        );
      })}
    </div>
  );
}

function ChatRuntimeVisual({
  architectureMode,
  projection,
  runStatus,
  executionEvents,
}: {
  architectureMode: ArchitectureMode;
  projection: {
    architectureView: Record<string, unknown>;
    activeActorName?: string | null;
  };
  runStatus?: string | null;
  executionEvents: RunExecutionEvent[];
}) {
  const activeActorName = projection.activeActorName ?? "runtime";
  const actors = (() => {
    const raw = projection.architectureView?.actors;
    return raw && typeof raw === "object" ? Object.values(raw) : [];
  })();
  const stages = (() => {
    const raw = projection.architectureView?.stages;
    return Array.isArray(raw) ? raw : [];
  })();
  const handoffs = (() => {
    const raw = projection.architectureView?.handoffs;
    return Array.isArray(raw) ? raw : [];
  })();

  if (architectureMode === "structured_workflow") {
    return <WorkflowFlow activeActorName={activeActorName} executionEvents={executionEvents} runStatus={runStatus} stages={stages} />;
  }
  if (architectureMode === "decentralized_swarm") {
    return <SwarmFlow activeActorName={activeActorName} actors={actors} executionEvents={executionEvents} handoffs={handoffs} runStatus={runStatus} />;
  }
  return <CentralizedFlow activeActorName={activeActorName} actors={actors} executionEvents={executionEvents} runStatus={runStatus} />;
}

function ArchitectureIcon({ mode }: { mode: ArchitectureMode }) {
  if (mode === "all_architectures") {
    return <Workflow className="h-3.5 w-3.5" />;
  }
  if (mode === "structured_workflow") {
    return <Workflow className="h-3.5 w-3.5" />;
  }
  if (mode === "decentralized_swarm") {
    return <Network className="h-3.5 w-3.5" />;
  }
  return <Bot className="h-3.5 w-3.5" />;
}

function ConversationStatusIcon({
  reviewPending,
  status
}: {
  reviewPending: boolean;
  status: ConversationSummary["status"];
}) {
  if (reviewPending || status === "human_review_required") {
    return <AlertTriangle className="h-3.5 w-3.5" />;
  }
  if (status === "completed") {
    return <CheckCircle2 className="h-3.5 w-3.5" />;
  }
  if (status === "waiting") {
    return <Clock3 className="h-3.5 w-3.5" />;
  }
  if (status === "error") {
    return <AlertTriangle className="h-3.5 w-3.5" />;
  }
  return <Activity className="h-3.5 w-3.5" />;
}

function getLayoutColumns(historyOpen: boolean): string {
  if (historyOpen) {
    return "lg:grid-cols-[300px_minmax(0,1fr)]";
  }
  return "lg:grid-cols-[56px_minmax(0,1fr)]";
}

function isArchitectureMode(value: string | null | undefined): value is ArchitectureMode {
  return architectureOptions.some((option) => option.value === value);
}

function statusVariant(status: ConversationSummary["status"]): BadgeProps["variant"] {
  if (status === "completed") {
    return "success";
  }
  if (status === "error") {
    return "destructive";
  }
  if (status === "waiting" || status === "human_review_required") {
    return "warning";
  }
  return "muted";
}

function shortId(id: string): string {
  return id.slice(0, 8);
}

function formatUpdatedAt(value: string): string {
  return new Date(value).toLocaleDateString("pt-BR", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "2-digit"
  });
}

function formatArchitectureLabel(mode: ArchitectureMode): string {
  return formatArchitectureLabelText(mode);
}

function hasArchitectureComparison(
  runs: Array<{ experiment?: Record<string, unknown> }>,
  architectureMode: ArchitectureMode,
): boolean {
  if (architectureMode === "all_architectures") {
    return true;
  }
  const keys = new Set(
    runs
      .map((run) => {
        const value = run.experiment?.architectureKey;
        return typeof value === "string" ? value : null;
      })
      .filter((value): value is string => Boolean(value)),
  );
  return keys.size > 1;
}

function buildLatestArchitectureRuns(runs: Run[]): Run[] {
  const map = new Map<Exclude<ArchitectureMode, "all_architectures">, Run>();
  for (const run of runs) {
    const architecture = readArchitectureKey(run);
    map.set(architecture, run);
  }
  const architectureOrder: Array<Exclude<ArchitectureMode, "all_architectures">> = [
    "centralized_orchestration",
    "structured_workflow",
    "decentralized_swarm",
  ];
  return architectureOrder
    .map((architecture) => map.get(architecture))
    .filter((run): run is Run => Boolean(run));
}

function readArchitectureKey(run: Run): Exclude<ArchitectureMode, "all_architectures"> {
  const value = run.experiment?.architectureKey;
  if (value === "structured_workflow" || value === "decentralized_swarm") {
    return value;
  }
  return "centralized_orchestration";
}

function readMessageRuntimeRunId(message: { metadata?: unknown }): string | null {
  const meta = message.metadata;
  if (!meta || typeof meta !== "object") return null;
  const value = (meta as Record<string, unknown>).runtimeRunId;
  return typeof value === "string" && value.length > 0 ? value : null;
}

/**
 * In multi-architecture mode every architecture produces its own outbound
 * message tagged with `metadata.runtimeRunId`. The chat view should show
 * the user's inbound messages plus only the outbound responses that belong
 * to the currently-selected architecture (across all turns), so switching
 * architectures swaps out the AI side of the conversation cleanly.
 */
function filterMessagesForArchitecture({
  messages,
  runs,
  isMultiArchitecture,
  selectedArchitectureKey,
  selectedFlowRunId,
}: {
  messages: Message[];
  runs: Run[];
  isMultiArchitecture: boolean;
  selectedArchitectureKey: Exclude<ArchitectureMode, "all_architectures"> | null;
  selectedFlowRunId: string | null;
}): Message[] {
  if (!isMultiArchitecture || !selectedArchitectureKey) {
    return messages;
  }
  const runIdToArchitecture = new Map<string, string>();
  for (const run of runs) {
    const key = run.experiment?.architectureKey;
    if (typeof key === "string") {
      runIdToArchitecture.set(run.id, key);
    }
  }
  return messages.filter((message) => {
    if (message.direction === "inbound") {
      return true;
    }
    if (message.id.startsWith("streaming-")) {
      const runId = message.id.slice("streaming-".length);
      return runId === selectedFlowRunId;
    }
    if (message.direction === "outbound") {
      const runId = readMessageRuntimeRunId(message);
      if (!runId) return false;
      return runIdToArchitecture.get(runId) === selectedArchitectureKey;
    }
    return true;
  });
}

function pickDisplayedExecution({
  selectedFlowRunId,
  selectedFlowExecution,
  runExecution,
  isMultiArchitecture,
}: {
  selectedFlowRunId: string | null;
  selectedFlowExecution: RunExecutionResponse | null;
  runExecution: RunExecutionResponse | null;
  isMultiArchitecture: boolean;
}): RunExecutionResponse | null {
  if (!selectedFlowRunId) return runExecution;
  // Prefer the explicitly fetched execution for the selected run when present.
  if (selectedFlowExecution?.run.id === selectedFlowRunId) {
    return selectedFlowExecution;
  }
  // If the live runExecution already matches the selected run, use it.
  if (runExecution?.run.id === selectedFlowRunId) {
    return runExecution;
  }
  // In multi-architecture mode, fall back to NULL rather than the canonical
  // run's execution. Showing the wrong architecture's flow while waiting for
  // the right one to load misleads the user; the placeholder is honest.
  if (isMultiArchitecture) {
    return null;
  }
  return runExecution;
}

function formatConversationPreview(value: string | null | undefined): string {
  if (!value) {
    return "Sem mensagens";
  }
  const normalized = value.trim();
  if (!normalized.startsWith("{")) {
    return normalized;
  }

  try {
    const parsed = JSON.parse(normalized) as {
      content?: Array<{ text?: string }>;
      role?: string;
    };
    const text = parsed.content
      ?.map((entry) => entry.text?.trim())
      .find((entry): entry is string => Boolean(entry));
    return text ?? parsed.role ?? normalized;
  } catch {
    const singleQuotedMatch = normalized.match(/'text':\s*'([^']+)/);
    const doubleQuotedMatch = normalized.match(/"text":\s*"([^"]+)/);
    return (
      singleQuotedMatch?.[1]
        ?.replaceAll("\\n", " ")
        .replaceAll("\\\\", "\\")
        .trim()
      ?? doubleQuotedMatch?.[1]
        ?.replaceAll("\\n", " ")
        .replaceAll("\\\\", "\\")
        .trim()
      ?? normalized
    );
  }
}
