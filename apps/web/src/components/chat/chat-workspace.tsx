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
  PanelRightClose,
  PanelRightOpen,
  Plus,
  Loader2,
  Search,
  Workflow
} from "lucide-react";

import { EventTimeline } from "@/components/events/event-timeline";
import { ConversationInspector } from "@/components/inspection/conversation-inspector";
import { CentralizedFlow, SwarmFlow, WorkflowFlow } from "@/components/runtime/architecture-flow";
import { RunExecutionPanel } from "@/components/runtime/run-execution-panel";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useConversation } from "@/hooks/use-conversation";
import type { ArchitectureMode, ConversationSummary, ExecutionMode, ReviewTask, ReviewTaskStatus, RunExecutionEvent } from "@/lib/types";
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
  { label: "Orquestração centralizada", value: "centralized_orchestration" },
  { label: "Workflow estruturado", value: "structured_workflow" },
  { label: "Swarm descentralizado", value: "decentralized_swarm" }
];

export function ChatWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isEventsOpen, setIsEventsOpen] = useState(false);
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);
  const [isDraftConversation, setIsDraftConversation] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [architectureMode, setArchitectureMode] = useState<ArchitectureMode>(
    "centralized_orchestration"
  );
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("mock");
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("conversa");
  const [isFlowOpen, setIsFlowOpen] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem("chat-flow-open") === "true";
  });
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
    ? getLayoutColumns(isHistoryOpen, isEventsOpen)
    : "lg:grid-cols-1";
  const requestedConversationId = searchParams.get("conversationId");
  const hasActiveConversation = Boolean(conversationId);

  function handleStartDraftConversation() {
    setIsDraftConversation(true);
    router.replace("/", { scroll: false });
    setIsInspectorOpen(false);
    setSelectedRunId(null);
    void startConversation();
  }

  useEffect(() => {
    localStorage.setItem("chat-flow-open", String(isFlowOpen));
  }, [isFlowOpen]);

  useEffect(() => {
    if (!runs.length) {
      setSelectedRunId(null);
      return;
    }
    setSelectedRunId((current) => current ?? runs[runs.length - 1].id);
  }, [runs]);

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
    setIsDraftConversation(false);
    router.replace(`/?conversationId=${conversationId}`, { scroll: false });
  }, [conversationId, requestedConversationId, router]);

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
            router.replace(`/?conversationId=${summary.conversationId}`, { scroll: false });
            setIsDraftConversation(false);
            if (isArchitectureMode(summary.architectureMode)) {
              setArchitectureMode(summary.architectureMode);
            }
            if (typeof window !== "undefined" && window.innerWidth < 1024) {
              setIsHistoryOpen(false);
            }
            void selectConversation(summary.conversationId);
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
                <HeaderContextTooltip architectureMode={architectureMode} />
              </div>
              <p className="truncate text-xs text-muted-foreground">
                {conversationId ? `Conversa ${conversationId}` : "Nenhuma conversa ativa"}
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {activeTab !== "atividade" ? (
            <Button
              className="lg:hidden"
              data-testid="events-toggle"
              onClick={() => setIsEventsOpen((current) => !current)}
              size="icon"
              type="button"
              variant="outline"
            >
              {isEventsOpen ? (
                <PanelRightClose className="h-4 w-4" />
              ) : (
                <PanelRightOpen className="h-4 w-4" />
              )}
            </Button>
            ) : null}
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

        {error ? (
          <Alert className="rounded-none border-x-0 border-t-0 px-5 py-2" variant="destructive">
            <AlertDescription>{error}</AlertDescription>
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
                {isFlowOpen ? (
                  runExecution?.projection ? (
                    <div
                      aria-label="Fluxo da arquitetura"
                      className="shrink-0 border-b bg-muted/30 p-2"
                      data-testid="chat-flow-panel"
                      style={{ minHeight: 260, maxHeight: 360, overflow: "auto" }}
                    >
                      <ChatRuntimeVisual
                        architectureMode={architectureMode}
                        projection={runExecution.projection}
                        executionEvents={runExecution.executionEvents ?? []}
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
                    messages={messages}
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
                <RunExecutionPanel
                  hideTabs
                  onSelectRun={setSelectedRunId}
                  runs={runs}
                  selectedRunId={selectedRunId}
                  variant="technical"
                />
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

      {activeTab === "conversa" ? (
        <EventTimeline
          architectureMode={architectureMode}
          connectionStatus={connectionStatus}
          events={events}
          isOpen={isEventsOpen}
          onOpenChange={setIsEventsOpen}
          reviewPanel={
            <ReviewPanel onResolve={updateReviewTask} reviewTasks={reviewTasks} />
          }
        />
      ) : null}
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
  onExecutionModeChange
}: {
  executionMode: ExecutionMode;
  onExecutionModeChange: (mode: ExecutionMode) => void;
}) {
  const isMock = executionMode === "mock";
  return (
    <button
      aria-label={`Modo de execução: ${isMock ? "Simulado" : "Real"}`}
      className="flex h-9 items-center gap-2 rounded-md border bg-background px-3 text-sm transition-colors hover:bg-muted"
      onClick={() => onExecutionModeChange(isMock ? "real" : "mock")}
      type="button"
    >
      <span
        className={`inline-block h-2 w-2 rounded-full ${
          isMock ? "bg-amber-400" : "bg-emerald-500"
        }`}
      />
      <span className="hidden sm:inline">{isMock ? "Simulado" : "Real"}</span>
    </button>
  );
}

function HeaderContextTooltip({ architectureMode }: { architectureMode: ArchitectureMode }) {
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
            <p>Runtime: mock runtime</p>
            <p>Arquitetura: {formatArchitectureMode(architectureMode)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function formatArchitectureMode(mode: ArchitectureMode): string {
  return architectureOptions.find((option) => option.value === mode)?.label ?? mode;
}

function ChatRuntimeVisual({
  architectureMode,
  projection,
  executionEvents,
}: {
  architectureMode: ArchitectureMode;
  projection: { architectureView: Record<string, unknown>; activeActorName?: string | null };
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
    return <WorkflowFlow activeActorName={activeActorName} stages={stages} executionEvents={executionEvents} />;
  }
  if (architectureMode === "decentralized_swarm") {
    return <SwarmFlow activeActorName={activeActorName} actors={actors} executionEvents={executionEvents} handoffs={handoffs} />;
  }
  return <CentralizedFlow activeActorName={activeActorName} actors={actors} executionEvents={executionEvents} />;
}

function ArchitectureIcon({ mode }: { mode: ArchitectureMode }) {
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

function getLayoutColumns(historyOpen: boolean, eventsOpen: boolean): string {
  if (historyOpen && eventsOpen) {
    return "lg:grid-cols-[300px_minmax(0,1fr)_420px]";
  }
  if (historyOpen && !eventsOpen) {
    return "lg:grid-cols-[300px_minmax(0,1fr)_56px]";
  }
  if (!historyOpen && eventsOpen) {
    return "lg:grid-cols-[56px_minmax(0,1fr)_420px]";
  }
  return "lg:grid-cols-[56px_minmax(0,1fr)_56px]";
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
  if (mode === "structured_workflow") {
    return "Workflow Estruturado";
  }
  if (mode === "decentralized_swarm") {
    return "Swarm Descentralizado";
  }
  return "Orquestração Centralizada";
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
