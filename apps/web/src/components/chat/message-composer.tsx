"use client";

import { FormEvent, useState } from "react";

interface MessageComposerProps {
  disabled: boolean;
  isSending: boolean;
  onSend: (text: string) => Promise<void>;
}

export function MessageComposer({ disabled, isSending, onSend }: MessageComposerProps) {
  const [text, setText] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!text.trim()) {
      return;
    }
    const currentText = text;
    setText("");
    await onSend(currentText);
  }

  return (
    <form className="border-t border-line bg-panel p-3" onSubmit={handleSubmit}>
      <div className="flex items-end gap-2">
        <textarea
          className="min-h-12 flex-1 resize-none border border-line bg-white px-3 py-2 text-sm text-ink outline-none focus:border-action"
          disabled={disabled || isSending}
          placeholder={disabled ? "Crie uma conversa para enviar mensagens" : "Digite sua mensagem"}
          rows={2}
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        <button
          className="h-12 border border-action bg-action px-4 text-sm font-medium text-white disabled:border-line disabled:bg-surface disabled:text-muted"
          disabled={disabled || isSending || !text.trim()}
          type="submit"
        >
          {isSending ? "Enviando" : "Enviar"}
        </button>
      </div>
    </form>
  );
}

