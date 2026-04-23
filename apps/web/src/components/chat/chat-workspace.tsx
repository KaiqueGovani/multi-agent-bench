"use client";

import { useState } from "react";
import {
  Activity,
  AlertTriangle,
  Bot,
  CheckCircle2,
  Clock3,
  Globe2,
  MessageSquare,
  Network,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  Plus,
  Loader2,
  Workflow
} from "lucide-react";

import { EventTimeline } from "@/components/events/event-timeline";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useConversation } from "@/hooks/use-conversation";
import type { ArchitectureMode, ConversationSummary } from "@/lib/types";
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
  const [architectureMode, setArchitectureMode] = useState<ArchitectureMode>(
    "centralized_orchestration"
  );
  const {
    attachmentsByMessage,
    connectionStatus,
    conversationId,
    conversationSummaries,
    error,
    events,
    isCreatingConversation,
    isSending,
    messages,
    sendMessage,
    selectConversation,
    startConversation
  } = useConversation(architectureMode);
  const layoutColumns = getLayoutColumns(isHistoryOpen, isEventsOpen);

  return (
    <main
      className={`grid min-h-screen grid-cols-1 overflow-hidden bg-background text-foreground lg:h-screen ${layoutColumns}`}
    >
      <ConversationHistory
        activeConversationId={conversationId}
        conversations={conversationSummaries}
        isOpen={isHistoryOpen}
        isCreatingConversation={isCreatingConversation}
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
        <header className="flex min-h-16 items-center border-b bg-card px-4 shadow-sm">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <Button
              className="lg:hidden"
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
            <div className="min-w-0">
              <h1 className="truncate text-base font-semibold">
                Atendimento farmaceutico POC
              </h1>
              <p className="truncate text-xs text-muted-foreground">
                {conversationId ? `Conversa ${conversationId}` : "Nenhuma conversa ativa"}
              </p>
            </div>
            <div className="hidden items-center gap-2 md:flex">
              <Badge className="gap-1" variant="outline">
                <Globe2 className="h-3.5 w-3.5" />
                web_chat
              </Badge>
              <Badge className="gap-1" variant="outline">
                <Bot className="h-3.5 w-3.5" />
                mock runtime
              </Badge>
              <Badge className="gap-1" variant="outline">
                <ArchitectureIcon mode={architectureMode} />
                {formatArchitectureMode(architectureMode)}
              </Badge>
              {events.length > 0 ? (
                <Badge className="gap-1">
                  <Activity className="h-3.5 w-3.5" />
                  {events.length} eventos
                </Badge>
              ) : null}
            </div>
          </div>
          <select
            className="mr-2 hidden h-9 max-w-52 rounded-md border bg-background px-3 text-sm text-foreground shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-ring md:block"
            disabled={isSending}
            onChange={(event) => setArchitectureMode(event.target.value as ArchitectureMode)}
            value={architectureMode}
          >
            {architectureOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <Button
            className="mr-2 lg:hidden"
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
            disabled={isCreatingConversation}
            onClick={() => void startConversation()}
            size="sm"
            type="button"
          >
            {isCreatingConversation ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Criando
              </>
            ) : (
              "Nova conversa"
            )}
          </Button>
        </header>

        {error ? (
          <Alert className="rounded-none border-x-0 border-t-0 px-5 py-2" variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        <div className="min-h-0 flex-1 overflow-y-auto bg-background">
          <MessageList
            attachmentsByMessage={attachmentsByMessage}
            messages={messages}
          />
        </div>

        <MessageComposer
          disabled={!conversationId}
          isSending={isSending}
          onSend={sendMessage}
        />
      </section>

      <EventTimeline
        architectureMode={architectureMode}
        connectionStatus={connectionStatus}
        events={events}
        isOpen={isEventsOpen}
        onOpenChange={setIsEventsOpen}
      />
    </main>
  );
}

function ConversationHistory({
  activeConversationId,
  conversations,
  isOpen,
  isCreatingConversation,
  onCreateConversation,
  onOpenChange,
  onSelectConversation
}: {
  activeConversationId: string | null;
  conversations: ConversationSummary[];
  isOpen: boolean;
  isCreatingConversation: boolean;
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
                        <span>{formatUpdatedAt(summary.updatedAt)}</span>
                      </div>
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
