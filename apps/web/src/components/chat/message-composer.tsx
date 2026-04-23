"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { FileText, Loader2, Paperclip, Send, X } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

interface MessageComposerProps {
  disabled: boolean;
  isSending: boolean;
  onSend: (text: string, files: File[]) => Promise<void>;
}

interface SelectedAttachment {
  file: File;
  previewUrl?: string;
}

const ACCEPTED_FILE_TYPES = ["image/jpeg", "image/png", "image/webp", "application/pdf"];
const MAX_FILES = 4;
const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;

export function MessageComposer({ disabled, isSending, onSend }: MessageComposerProps) {
  const [text, setText] = useState("");
  const [attachments, setAttachments] = useState<SelectedAttachment[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const attachmentsRef = useRef<SelectedAttachment[]>([]);

  const canSubmit = useMemo(() => {
    return Boolean(text.trim()) || attachments.length > 0;
  }, [attachments.length, text]);

  useEffect(() => {
    attachmentsRef.current = attachments;
  }, [attachments]);

  useEffect(() => {
    return () => {
      for (const attachment of attachmentsRef.current) {
        if (attachment.previewUrl) {
          URL.revokeObjectURL(attachment.previewUrl);
        }
      }
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }
    const currentText = text;
    const currentFiles = attachments.map((attachment) => attachment.file);
    for (const attachment of attachments) {
      if (attachment.previewUrl) {
        URL.revokeObjectURL(attachment.previewUrl);
      }
    }
    setText("");
    setAttachments([]);
    setFileInputKey((current) => current + 1);
    await onSend(currentText, currentFiles);
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selectedFiles = Array.from(event.target.files ?? []);
    event.target.value = "";
    setFileError(null);

    if (selectedFiles.length === 0) {
      return;
    }

    const nextAttachments = [...attachments];
    for (const file of selectedFiles) {
      if (nextAttachments.length >= MAX_FILES) {
        setFileError(`Limite de ${MAX_FILES} arquivos por mensagem.`);
        break;
      }
      if (!ACCEPTED_FILE_TYPES.includes(file.type)) {
        setFileError("Formatos aceitos: JPG, PNG, WebP ou PDF.");
        continue;
      }
      if (file.size > MAX_FILE_SIZE_BYTES) {
        setFileError("Cada arquivo deve ter ate 5 MB.");
        continue;
      }
      nextAttachments.push({
        file,
        previewUrl: file.type.startsWith("image/") ? URL.createObjectURL(file) : undefined
      });
    }

    setAttachments(nextAttachments);
  }

  function removeAttachment(index: number) {
    setAttachments((current) => {
      const attachment = current[index];
      if (attachment?.previewUrl) {
        URL.revokeObjectURL(attachment.previewUrl);
      }
      return current.filter((_, currentIndex) => currentIndex !== index);
    });
  }

  return (
    <form className="border-t bg-card/95 p-3 shadow-sm" onSubmit={handleSubmit}>
      <div className="mx-auto w-full max-w-5xl">
        {attachments.length > 0 ? (
          <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {attachments.map((attachment, index) => (
              <Card className="relative overflow-hidden" key={`${attachment.file.name}-${index}`}>
                <CardContent className="p-0">
                  {attachment.previewUrl ? (
                    <img
                      alt={attachment.file.name}
                      className="h-24 w-full object-cover"
                      src={attachment.previewUrl}
                    />
                  ) : (
                    <div className="flex h-24 items-center justify-center bg-muted">
                      <FileText className="h-8 w-8 text-muted-foreground" />
                    </div>
                  )}
                  <Button
                    className="absolute right-1 top-1 h-7 w-7"
                    disabled={disabled || isSending}
                    onClick={() => removeAttachment(index)}
                    size="icon"
                    type="button"
                    variant="secondary"
                  >
                    <X className="h-3.5 w-3.5" />
                  </Button>
                  <div className="p-2">
                    <p className="truncate text-xs">{attachment.file.name}</p>
                    <p className="text-[11px] text-muted-foreground">{formatBytes(attachment.file.size)}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : null}

        {fileError ? (
          <Alert className="mb-2 py-2" variant="warning">
            <AlertDescription>{fileError}</AlertDescription>
          </Alert>
        ) : null}

        <div className="grid w-full grid-cols-[auto_minmax(0,1fr)_auto] items-stretch gap-2">
          <Input
            accept={ACCEPTED_FILE_TYPES.join(",")}
            className="hidden"
            disabled={disabled || isSending}
            key={fileInputKey}
            multiple
            onChange={handleFileChange}
            ref={fileInputRef}
            type="file"
          />
          <Button
            className="h-full min-h-20 self-stretch px-3"
            disabled={disabled || isSending}
            onClick={() => fileInputRef.current?.click()}
            type="button"
            variant="outline"
          >
            <Paperclip className="h-4 w-4" />
            <span className="hidden sm:inline">Anexar</span>
          </Button>
          <Textarea
            className="min-h-20 resize-none text-sm"
            disabled={disabled || isSending}
            placeholder={disabled ? "Crie uma conversa para enviar mensagens" : "Digite sua mensagem"}
            rows={3}
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
          <Button
            className="h-full min-h-20 self-stretch px-3"
            disabled={disabled || isSending || !canSubmit}
            type="submit"
          >
            {isSending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <Send className="h-4 w-4" />
                <span className="hidden sm:inline">Enviar</span>
              </>
            )}
          </Button>
        </div>
      </div>
    </form>
  );
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
