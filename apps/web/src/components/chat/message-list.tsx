import type { Message } from "@/lib/types";

interface MessageListProps {
  messages: Message[];
  attachmentCountByMessage: Record<string, number>;
}

export function MessageList({ messages, attachmentCountByMessage }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-sm text-muted">
        Inicie uma conversa e envie uma mensagem para acompanhar o processamento.
      </div>
    );
  }

  return (
    <div className="space-y-3 p-4">
      {messages.map((message) => {
        const isInbound = message.direction === "inbound";
        return (
          <article
            key={message.id}
            className={`max-w-[78%] border px-4 py-3 ${
              isInbound
                ? "ml-auto border-action bg-cyan-50"
                : "mr-auto border-line bg-panel"
            }`}
          >
            <div className="mb-1 flex items-center justify-between gap-3 text-xs text-muted">
              <span>{isInbound ? "Usuario" : "Sistema"}</span>
              <span>{message.status}</span>
            </div>
            <p className="whitespace-pre-wrap text-sm leading-6 text-ink">
              {message.contentText || "(sem texto)"}
            </p>
            {attachmentCountByMessage[message.id] ? (
              <p className="mt-2 text-xs text-muted">
                {attachmentCountByMessage[message.id]} anexo(s)
              </p>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}

