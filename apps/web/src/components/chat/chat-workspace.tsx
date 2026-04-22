"use client";

import { EventTimeline } from "@/components/events/event-timeline";
import { useConversation } from "@/hooks/use-conversation";
import { MessageComposer } from "./message-composer";
import { MessageList } from "./message-list";

export function ChatWorkspace() {
  const {
    attachmentCountByMessage,
    connectionStatus,
    conversationId,
    error,
    events,
    isSending,
    messages,
    sendMessage,
    startConversation
  } = useConversation();

  return (
    <main className="grid min-h-screen grid-cols-1 bg-surface text-ink lg:h-screen lg:grid-cols-[minmax(0,1fr)_380px]">
      <section className="flex min-w-0 flex-col">
        <header className="flex items-center justify-between border-b border-line bg-panel px-5 py-3">
          <div>
            <h1 className="text-base font-semibold">Atendimento farmaceutico POC</h1>
            <p className="text-xs text-muted">
              {conversationId ? `Conversa ${conversationId}` : "Nenhuma conversa ativa"}
            </p>
          </div>
          <button
            className="border border-action px-3 py-2 text-sm font-medium text-action disabled:border-line disabled:text-muted"
            disabled={Boolean(conversationId)}
            onClick={() => void startConversation()}
            type="button"
          >
            Nova conversa
          </button>
        </header>

        {error ? (
          <div className="border-b border-danger bg-red-50 px-5 py-2 text-sm text-danger">
            {error}
          </div>
        ) : null}

        <div className="min-h-0 flex-1 overflow-y-auto">
          <MessageList
            attachmentCountByMessage={attachmentCountByMessage}
            messages={messages}
          />
        </div>

        <MessageComposer
          disabled={!conversationId}
          isSending={isSending}
          onSend={sendMessage}
        />
      </section>

      <EventTimeline events={events} connectionStatus={connectionStatus} />
    </main>
  );
}
