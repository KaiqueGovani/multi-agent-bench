import { getAttachmentUrl } from "@/lib/api/client";
import type { Attachment, Message } from "@/lib/types";

interface MessageListProps {
  messages: Message[];
  attachmentsByMessage: Record<string, Attachment[]>;
}

export function MessageList({ messages, attachmentsByMessage }: MessageListProps) {
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
            {attachmentsByMessage[message.id]?.length ? (
              <div className="mt-3 grid grid-cols-2 gap-2">
                {attachmentsByMessage[message.id].map((attachment) => (
                  <a
                    className="block border border-line bg-white"
                    href={getAttachmentUrl(attachment.id)}
                    key={attachment.id}
                    rel="noreferrer"
                    target="_blank"
                  >
                    <img
                      alt={attachment.originalFilename}
                      className="h-28 w-full object-cover"
                      src={getAttachmentUrl(attachment.id)}
                    />
                    <p className="truncate px-2 py-1 text-xs text-muted">
                      {attachment.originalFilename}
                    </p>
                  </a>
                ))}
              </div>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}
