import { useEffect, useRef, useState } from "react";
import { getAttachmentUrl } from "@/lib/api/client";
import { MarkdownContent } from "@/components/common/markdown-content";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { Attachment, Message, ReviewTask } from "@/lib/types";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Clock3,
  Copy,
  Check,
  FileText,
  Image as ImageIcon,
  Loader2,
  MessageCircle,
  ShieldAlert,
  User
} from "lucide-react";

interface MessageListProps {
  messages: Message[];
  attachmentsByMessage: Record<string, Attachment[]>;
  isLoading?: boolean;
  reviewTasks?: ReviewTask[];
}

const MESSAGE_STATUS_LABELS: Record<Message["status"], string> = {
  draft: "Rascunho",
  received: "Recebida",
  accepted: "Aceita",
  validating: "Validando",
  processing: "Em processamento",
  forwarded: "Encaminhada",
  waiting: "Aguardando",
  completed: "Concluída",
  error: "Falhou",
  human_review_required: "Revisão necessária"
};

export function MessageList({
  messages,
  attachmentsByMessage,
  isLoading = false,
  reviewTasks = [],
}: MessageListProps) {
  const listRef = useRef<HTMLDivElement | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [copyError, setCopyError] = useState<string | null>(null);
  const hasMessages = messages.length > 0;

  async function copyResponse(message: Message) {
    try {
      await navigator.clipboard.writeText(formatMessageContent(message.contentText));
      setCopiedId(message.id);
      setCopyError(null);
    } catch {
      setCopyError("Não foi possível copiar. Selecione o texto da resposta para copiar manualmente.");
    }
  }

  useEffect(() => {
    if (isLoading || !hasMessages) return;
    const list = listRef.current;
    const viewport = list?.parentElement;
    if (!list || !viewport) return;

    let followLatest = true;
    const handleScroll = () => {
      followLatest = viewport.scrollHeight - viewport.clientHeight - viewport.scrollTop < 48;
    };
    const scrollToLatest = () => {
      if (followLatest) viewport.scrollTop = viewport.scrollHeight;
    };

    // Streamed text changes the list height. The graph opening changes the
    // viewport height. Follow both while the reader is at the latest message.
    const observer = new ResizeObserver(scrollToLatest);
    observer.observe(list);
    observer.observe(viewport);
    viewport.addEventListener("scroll", handleScroll, { passive: true });
    scrollToLatest();

    return () => {
      observer.disconnect();
      viewport.removeEventListener("scroll", handleScroll);
    };
  }, [hasMessages, isLoading]);

  if (isLoading) {
    return (
      <div
        className="mx-auto flex w-full max-w-5xl flex-col gap-4 p-4 md:p-6"
        data-testid="message-list-loading"
      >
        <MessageSkeleton align="left" />
        <MessageSkeleton align="right" />
        <MessageSkeleton align="left" />
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-6" data-testid="message-list-empty">
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
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-4 p-4 md:p-6" data-testid="message-list" ref={listRef}>
      {messages.map((message) => {
        const isInbound = message.direction === "inbound";
        const isStreaming = message.id.startsWith("streaming-");
        const isImported = message.metadata?.importedHistory === true;
        const belongsToReviewedTurn = (task: ReviewTask) => {
          if (task.messageId === message.id || task.messageId === message.metadata?.sourceMessageId) return true;
          const reviewedMessage = messages.find((entry) => entry.id === task.messageId);
          return reviewedMessage?.correlationId === message.correlationId;
        };
        const review = !isImported ? [...reviewTasks].sort((a, b) => b.createdAt.localeCompare(a.createdAt)).find((task) => {
          const reviewedRunId = task.metadata?.runtimeRunId;
          if (!isInbound && typeof reviewedRunId === "string") {
            return message.metadata?.runtimeRunId === reviewedRunId;
          }
          return belongsToReviewedTurn(task);
        }) : undefined;
        const comparisonReview = !isImported && !isInbound && !review && typeof message.metadata?.runtimeRunId === "string"
          ? [...reviewTasks].sort((a, b) => b.createdAt.localeCompare(a.createdAt)).find((task) => typeof task.metadata?.runtimeRunId === "string"
            && task.metadata.runtimeRunId !== message.metadata.runtimeRunId && belongsToReviewedTurn(task))
          : undefined;
        const comparisonPending = comparisonReview?.status === "open" || comparisonReview?.status === "in_review";
        const comparisonLabel = comparisonReview ? comparisonPending ? "Comparação · atendimento em revisão" : comparisonReview.status === "resolved" ? "Comparação · atendimento revisado" : "Comparação · atendimento não aprovado" : undefined;
        const awaitingReview = review?.status === "open" || review?.status === "in_review";
        const reviewApproved = review?.status === "resolved";
        const reviewRejected = review?.status === "cancelled";
        const reviewLabel = awaitingReview ? isInbound ? "Encaminhada para revisão" : "Aguardando revisão humana" : reviewApproved ? "Revisão aprovada" : reviewRejected ? "Revisão não aprovada" : undefined;
        const author = isImported ? (isInbound ? "Cliente · WhatsApp" : "Atendente · WhatsApp") : (isInbound ? "Usuário" : "Resposta sugerida pelo MAB");
        return (
          <article
            data-testid={`message-${message.id}`}
            key={message.id}
            className={`flex gap-3 ${isInbound ? "justify-end" : "justify-start"}`}
            {...(isStreaming ? { "aria-live": "polite" } : {})}
          >
            {!isInbound ? (
              <div
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-secondary text-xs font-semibold text-secondary-foreground"
              >
                <Bot className="h-4 w-4" />
              </div>
            ) : null}
            <div className={`min-w-0 max-w-[min(36rem,82vw)] ${isInbound ? "items-end" : "items-start"} flex flex-col`}>
            <div className={`mb-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground ${isInbound ? "justify-end" : ""}`}>
              <span className="flex items-center gap-1">
                {isInbound ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
                {author}
              </span>
              <Badge className="gap-1" data-status={awaitingReview ? "human_review_required" : message.status} data-review-context={comparisonReview?.status} data-testid={reviewLabel || comparisonLabel ? `message-review-status-${message.id}` : undefined} variant={awaitingReview || comparisonPending ? "warning" : reviewRejected ? "destructive" : reviewApproved ? "success" : comparisonReview ? "muted" : "outline"}>
                {awaitingReview || comparisonPending ? <ShieldAlert aria-hidden="true" className="h-3.5 w-3.5" /> : reviewApproved ? <CheckCircle2 aria-hidden="true" className="h-3.5 w-3.5" /> : comparisonReview ? <MessageCircle aria-hidden="true" className="h-3.5 w-3.5" /> : <MessageStatusIcon status={message.status} />}
                {reviewLabel ?? comparisonLabel ?? MESSAGE_STATUS_LABELS[message.status]}
              </Badge>
            </div>
            <div
              className={`min-w-0 max-w-full rounded-lg border px-4 py-3 text-sm leading-6 shadow-sm [overflow-wrap:anywhere] ${
                isInbound
                  ? "border-primary bg-primary text-primary-foreground"
                  : awaitingReview ? "border-amber-300 bg-amber-50/70 text-card-foreground" : reviewRejected ? "border-destructive/30 bg-destructive/5 text-card-foreground" : "bg-card text-card-foreground"
              }`}
            >
              {!isInbound && awaitingReview ? <p className="mb-2 flex items-center gap-1.5 border-b border-amber-200 pb-2 text-xs font-medium leading-relaxed text-amber-900"><ShieldAlert aria-hidden="true" className="h-3.5 w-3.5 shrink-0" /> Sugestão ainda não aprovada por uma pessoa.</p> : null}
              {!isInbound && reviewRejected ? <p className="mb-2 text-xs font-medium text-destructive">Esta sugestão não foi aprovada na revisão humana.</p> : null}
              <MarkdownContent
                className="text-sm"
                content={formatMessageContent(message.contentText)}
                isStreaming={isStreaming && message.status === "processing"}
              />

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
            <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
              <span>{(message.createdAtClient || message.createdAtServer) ? new Date(message.createdAtClient || message.createdAtServer).toLocaleTimeString("pt-BR") : ""}</span>
              {!isInbound && !isImported && !isStreaming && message.contentText ? (
                <button
                  type="button"
                  aria-label="Copiar resposta"
                  className="inline-flex items-center gap-1 rounded px-1 py-1 hover:text-foreground focus-visible:outline focus-visible:outline-2"
                  onClick={() => void copyResponse(message)}
                >
                  {copiedId === message.id ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                  <span role="status">{copiedId === message.id ? "Copiada" : "Copiar resposta"}</span>
                </button>
              ) : null}
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
      {copyError ? <p role="alert" className="text-sm text-destructive">{copyError}</p> : null}
    </div>
  );
}

function MessageSkeleton({ align }: { align: "left" | "right" }) {
  const isRight = align === "right";

  return (
    <div className={`flex gap-3 ${isRight ? "justify-end" : "justify-start"}`}>
      {!isRight ? <Skeleton className="h-9 w-9 shrink-0" /> : null}
      <div className={`flex w-full max-w-[min(36rem,82vw)] flex-col gap-2 ${isRight ? "items-end" : "items-start"}`}>
        <Skeleton className="h-3 w-32" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-3 w-20" />
      </div>
      {isRight ? <Skeleton className="h-9 w-9 shrink-0" /> : null}
    </div>
  );
}

function MessageStatusIcon({ status }: { status: Message["status"] }) {
  if (status === "completed") {
    return <CheckCircle2 className="h-3.5 w-3.5" />;
  }
  if (status === "processing" || status === "accepted" || status === "validating") {
    return <Loader2 aria-hidden="true" className="h-3.5 w-3.5 motion-safe:animate-spin" />;
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

function formatMessageContent(value: string | null | undefined): string {
  if (!value) {
    return "(sem texto)";
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
        ?.replaceAll("\\n", "\n")
        .replaceAll("\\\\", "\\")
        .trim()
      ?? doubleQuotedMatch?.[1]
        ?.replaceAll("\\n", "\n")
        .replaceAll("\\\\", "\\")
        .trim()
      ?? normalized
    );
  }
}
