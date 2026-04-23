"use client";

import { useState } from "react";
import { PanelRightClose, PanelRightOpen } from "lucide-react";

import { EventTimeline } from "@/components/events/event-timeline";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useConversation } from "@/hooks/use-conversation";
import type { ArchitectureMode } from "@/lib/types";
import { MessageComposer } from "./message-composer";
import { MessageList } from "./message-list";

const architectureOptions: Array<{ label: string; value: ArchitectureMode }> = [
  { label: "Orquestracao centralizada", value: "centralized_orchestration" },
  { label: "Workflow estruturado", value: "structured_workflow" },
  { label: "Swarm descentralizado", value: "decentralized_swarm" }
];

export function ChatWorkspace() {
  const [isEventsOpen, setIsEventsOpen] = useState(true);
  const [architectureMode, setArchitectureMode] = useState<ArchitectureMode>(
    "centralized_orchestration"
  );
  const {
    attachmentsByMessage,
    connectionStatus,
    conversationId,
    error,
    events,
    isSending,
    messages,
    sendMessage,
    startConversation
  } = useConversation(architectureMode);

  return (
    <main
      className={`grid min-h-screen grid-cols-1 overflow-hidden bg-background text-foreground lg:h-screen ${
        isEventsOpen ? "lg:grid-cols-[minmax(0,1fr)_420px]" : "lg:grid-cols-[minmax(0,1fr)_56px]"
      }`}
    >
      <section className="flex min-w-0 flex-col">
        <header className="flex min-h-16 items-center border-b bg-card px-4 shadow-sm">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <div className="min-w-0">
              <h1 className="truncate text-base font-semibold">
                Atendimento farmaceutico POC
              </h1>
              <p className="truncate text-xs text-muted-foreground">
                {conversationId ? `Conversa ${conversationId}` : "Nenhuma conversa ativa"}
              </p>
            </div>
            <div className="hidden items-center gap-2 md:flex">
              <Badge variant="outline">web_chat</Badge>
              <Badge variant="outline">mock runtime</Badge>
              <Badge variant="outline">{formatArchitectureMode(architectureMode)}</Badge>
              {events.length > 0 ? (
                <Badge>{events.length} eventos</Badge>
              ) : null}
            </div>
          </div>
          <select
            className="mr-2 hidden h-9 max-w-52 rounded-md border bg-background px-3 text-sm text-foreground shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-ring md:block"
            disabled={Boolean(conversationId)}
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
            disabled={Boolean(conversationId)}
            onClick={() => void startConversation()}
            size="sm"
            type="button"
          >
            Nova conversa
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

function formatArchitectureMode(mode: ArchitectureMode): string {
  return architectureOptions.find((option) => option.value === mode)?.label ?? mode;
}
