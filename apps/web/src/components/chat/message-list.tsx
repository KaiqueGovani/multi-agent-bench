import { getAttachmentUrl } from "@/lib/api/client";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardTitle } from "@/components/ui/card";
import type { Attachment, Message } from "@/lib/types";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Clock3,
  FileText,
  Image as ImageIcon,
  Loader2,
  MessageCircle,
  User
} from "lucide-react";

interface MessageListProps {
  messages: Message[];
  attachmentsByMessage: Record<string, Attachment[]>;
}

export function MessageList({ messages, attachmentsByMessage }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-6">
        <Card className="max-w-md border-dashed text-center">
          <CardContent className="p-6">
            <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-md bg-muted">
              <MessageCircle className="h-5 w-5 text-muted-foreground" />
            </div>
            <CardTitle className="text-base">
              Nenhuma mensagem ainda
            </CardTitle>
            <CardDescription className="mt-2">
              Inicie uma conversa e envie texto, imagem ou PDF para acompanhar o processamento.
            </CardDescription>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-4 p-4 md:p-6">
      {messages.map((message) => {
        const isInbound = message.direction === "inbound";
        return (
          <article
            key={message.id}
            className={`flex gap-3 ${isInbound ? "justify-end" : "justify-start"}`}
          >
            {!isInbound ? (
              <div
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-secondary text-xs font-semibold text-secondary-foreground"
              >
                <Bot className="h-4 w-4" />
              </div>
            ) : null}
            <div className={`max-w-[min(36rem,82vw)] ${isInbound ? "items-end" : "items-start"} flex flex-col`}>
            <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                {isInbound ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
                {isInbound ? "Usuario" : "Sistema"}
              </span>
              <Badge className="gap-1" variant="outline">
                <MessageStatusIcon status={message.status} />
                {message.status}
              </Badge>
            </div>
            <div
              className={`rounded-lg border px-4 py-3 text-sm leading-6 shadow-sm ${
                isInbound
                  ? "border-primary bg-primary text-primary-foreground"
                  : "bg-card text-card-foreground"
              }`}
            >
              <p className="whitespace-pre-wrap">{message.contentText || "(sem texto)"}</p>
              {attachmentsByMessage[message.id]?.length ? (
                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {attachmentsByMessage[message.id].map((attachment) => (
                    <a
                      className="group overflow-hidden rounded-md border bg-card text-card-foreground"
                      href={getAttachmentUrl(attachment.id)}
                      key={attachment.id}
                      rel="noreferrer"
                      target="_blank"
                    >
                      {attachment.mimeType.startsWith("image/") ? (
                        <div className="relative">
                          <img
                            alt={attachment.originalFilename}
                            className="h-28 w-full object-cover"
                            src={getAttachmentUrl(attachment.id)}
                          />
                          <Badge className="absolute left-2 top-2 gap-1" variant="secondary">
                            <ImageIcon className="h-3 w-3" />
                            imagem
                          </Badge>
                        </div>
                      ) : (
                        <div className="flex h-28 items-center justify-center bg-muted">
                          <FileText className="h-8 w-8 text-muted-foreground" />
                        </div>
                      )}
                      <p className="truncate px-2 py-1 text-xs text-muted-foreground group-hover:text-foreground">
                        {attachment.originalFilename}
                      </p>
                      <p className="px-2 pb-2 text-[11px] text-muted-foreground">
                        {formatBytes(attachment.sizeBytes)}
                      </p>
                    </a>
                  ))}
                </div>
              ) : null}
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              {new Date(message.createdAtServer).toLocaleTimeString("pt-BR")}
            </div>
            </div>
            {isInbound ? (
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary text-xs font-semibold text-primary-foreground">
                <User className="h-4 w-4" />
              </div>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}

function MessageStatusIcon({ status }: { status: Message["status"] }) {
  if (status === "completed") {
    return <CheckCircle2 className="h-3.5 w-3.5" />;
  }
  if (status === "processing" || status === "accepted" || status === "validating") {
    return <Loader2 className="h-3.5 w-3.5 animate-spin" />;
  }
  if (status === "error" || status === "human_review_required") {
    return <AlertTriangle className="h-3.5 w-3.5" />;
  }
  return <Clock3 className="h-3.5 w-3.5" />;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const kilobytes = bytes / 1024;
  if (kilobytes < 1024) {
    return `${kilobytes.toFixed(1)} KB`;
  }
  return `${(kilobytes / 1024).toFixed(1)} MB`;
}
