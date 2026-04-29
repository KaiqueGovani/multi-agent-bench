"use client";

import { useEffect, useState } from "react";
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

import { PocDashboard } from "@/components/dashboard/poc-dashboard";
import { EventTimeline } from "@/components/events/event-timeline";
import { ConversationInspector } from "@/components/inspection/conversation-inspector";
import { RunExecutionPanel } from "@/components/runtime/run-execution-panel";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useConversation } from "@/hooks/use-conversation";
import type { ArchitectureMode, ConversationSummary, ReviewTask } from "@/lib/types";
import { MessageComposer } from "./message-composer";
import { MessageList } from "./message-list";

const architectureOptions: Array<{ label: string; value: ArchitectureMode }> = [
  { label: "Orquestracao centralizada", value: "centralized_orchestration" },
  { label: "Workflow estruturado", value: "structured_workflow" },
  { label: "Swarm descentralizado", value: "decentralized_swarm" }
];

export function ChatWorkspace() {
  const [isHistoryOpen, setIsHistoryOpen] = useState(true);
  const [isEventsOpen, setIsEventsOpen] = useState(true);
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);
  const [isDashboardOpen, setIsDashboardOpen] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [architectureMode, setArchitectureMode] = useState<ArchitectureMode>(
    "centralized_orchestration"
  );
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
    runs,
    sendMessage,
    selectConversation,
    startConversation,
    updateReviewTask
  } = useConversation(architectureMode);
  const layoutColumns = getLayoutColumns(isHistoryOpen, isEventsOpen);

  useEffect(() => {
    if (!runs.length) {
      setSelectedRunId(null);
      return;
    }
    setSelectedRunId((current) => current ?? runs[runs.length - 1].id);
  }, [runs]);

  return (
    <main
      className={`grid min-h-screen grid-cols-1 overflow-hidden bg-background text-foreground lg:h-screen ${layoutColumns}`}
    >
      <ConversationHistory
        activeConversationId={conversationId}
        conversations={conversationSummaries}
        isOpen={isHistoryOpen}
        isCreatingConversation={isCreatingConversation}
        isLoadingConversation={isLoadingConversation}
        openReviewCount={openReviewTasks.length}
        onCreateConversation={() => void startConversation()}
        onOpenChange={setIsHistoryOpen}
        onSelectConversation={(summary) => {
          if (isArchitectureMode(summary.architectureMode)) {
            setArchitectureMode(summary.architectureMode);
          }
          void selectConversation(summary.conversationId);
        }}
      />

      <section className="flex min-w-0 flex-col">
        <header className="flex min-h-16 items-center gap-3 border-b bg-card px-3 py-2 shadow-sm sm:px-4">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <Button
              className="shrink-0 lg:hidden"
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
                  Atendimento farmaceutico POC
                </h1>
                <HeaderContextTooltip architectureMode={architectureMode} />
              </div>
              <p className="truncate text-xs text-muted-foreground">
                {conversationId ? `Conversa ${conversationId}` : "Nenhuma conversa ativa"}
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button
              className="lg:hidden"
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
            <Button
              disabled={!conversationId}
              onClick={() => setIsInspectorOpen(true)}
              size="sm"
              type="button"
              variant="outline"
            >
              <Search className="h-4 w-4" />
              <span className="hidden sm:inline">Inspecao</span>
            </Button>
            <Button
              onClick={() => setIsDashboardOpen(true)}
              size="sm"
              type="button"
              variant="outline"
            >
              <BarChart3 className="h-4 w-4" />
              <span className="hidden sm:inline">Dashboard</span>
            </Button>
            <Button
              disabled={isCreatingConversation}
              onClick={() => void startConversation()}
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
        <PocDashboard
          isOpen={isDashboardOpen}
          onOpenChange={setIsDashboardOpen}
          onResolveReviewTask={(reviewTaskId, status, note) =>
            void updateReviewTask(reviewTaskId, status, note)
          }
          reviewTasks={openReviewTasks}
          onSelectConversation={(id) => void selectConversation(id)}
        />

        <div className="min-h-0 flex-1 overflow-y-auto bg-background">
          {runs.length > 0 ? (
            <RunExecutionPanel
              onSelectRun={setSelectedRunId}
              runs={runs}
              selectedRunId={selectedRunId}
            />
          ) : null}
          <MessageList
            attachmentsByMessage={attachmentsByMessage}
            isLoading={isLoadingConversation}
            messages={messages}
          />
        </div>

        <MessageComposer
          architectureMode={architectureMode}
          disabled={!conversationId}
          isSending={isSending}
          onArchitectureModeChange={setArchitectureMode}
          onSend={sendMessage}
        />
      </section>

      <EventTimeline
        architectureMode={architectureMode}
        connectionStatus={connectionStatus}
        events={events}
        isOpen={isEventsOpen}
        onOpenChange={setIsEventsOpen}
        reviewPanel={
          <ReviewPanel reviewTasks={reviewTasks} />
        }
      />
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
    <aside className="flex min-h-[220px] flex-col border-b bg-card lg:min-h-0 lg:border-b-0 lg:border-r">
      <div className="flex items-center justify-between gap-2 border-b px-3 py-3">
        {isOpen ? (
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold">Conversas</h2>
            <p className="truncate text-xs text-muted-foreground">
              {conversations.length} recentes
              {openReviewCount > 0 ? ` - ${openReviewCount} revisoes abertas` : ""}
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
                          {summary.reviewPending ? "revisao" : summary.status}
                        </Badge>
                      </div>
                      <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">
                        {summary.lastMessage ?? "Sem mensagens"}
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
  reviewTasks
}: {
  reviewTasks: ReviewTask[];
}) {
  const openTasks = reviewTasks.filter(
    (task) => task.status === "open" || task.status === "in_review"
  );
  const hasOpenTasks = openTasks.length > 0;
  const [isExpanded, setIsExpanded] = useState(hasOpenTasks);

  if (reviewTasks.length === 0) {
    return null;
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
              {hasOpenTasks ? "Acao humana necessaria" : "Revisao humana concluida"}
            </h3>
          </div>
          <p
            className={`mt-1 text-xs ${
              hasOpenTasks ? "text-amber-900" : "text-muted-foreground"
            }`}
          >
            {hasOpenTasks
              ? "Revise a solicitacao e escolha uma decisao rapida. A observacao e opcional."
              : "Nao ha pendencias humanas abertas nesta conversa."}
          </p>
        </button>
        <div className="flex shrink-0 items-center gap-2">
          <Badge variant={hasOpenTasks ? "warning" : "success"}>
            {hasOpenTasks ? `${openTasks.length} pendente` : "sem pendencias"}
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

          return (
            <div className="rounded-md border bg-background p-3" key={task.id}>
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-xs font-medium">{task.reason}</p>
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    Mensagem {shortId(task.messageId)} - {formatUpdatedAt(task.createdAt)}
                  </p>
                </div>
                <Badge variant={isOpen ? "warning" : "success"}>{task.status}</Badge>
              </div>
              {isOpen ? (
                <p className="mt-2 text-[11px] text-amber-800">
                  Um profissional esta avaliando a resposta.
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
