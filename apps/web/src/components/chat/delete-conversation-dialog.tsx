"use client";

import { Loader2, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";

export function DeleteConversationDialog({
  conversation,
  onClose,
  onDelete,
}: {
  conversation: { id: string; title: string };
  onClose: () => void;
  onDelete: (id: string) => Promise<void>;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const busyRef = useRef(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => { dialog?.close(); };
  }, []);

  async function confirmDelete() {
    if (busyRef.current) return;
    busyRef.current = true;
    setIsDeleting(true);
    setError(null);
    try {
      await onDelete(conversation.id);
      onClose();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Não foi possível excluir a conversa. Tente novamente.");
    } finally {
      busyRef.current = false;
      setIsDeleting(false);
    }
  }

  return (
    <dialog
      aria-describedby="delete-conversation-description"
      aria-labelledby="delete-conversation-title"
      className="fixed inset-0 m-auto w-[calc(100%_-_2rem)] max-w-md rounded-xl border bg-card p-5 text-card-foreground shadow-xl backdrop:bg-black/50"
      onCancel={(event) => { event.preventDefault(); if (!busyRef.current) onClose(); }}
      ref={dialogRef}
    >
      <h2 className="text-base font-semibold" id="delete-conversation-title">Excluir conversa?</h2>
      <p className="mt-3 break-words text-sm font-medium">{conversation.title}</p>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground" id="delete-conversation-description">
        A conversa, suas mensagens, anexos e todas as execuções serão excluídos. Esta ação não pode ser desfeita.
      </p>
      {error ? <p className="mt-3 rounded-md border border-destructive/40 p-3 text-sm text-destructive" role="alert">{error}</p> : null}
      <div className="mt-5 flex flex-wrap justify-end gap-2">
        <Button autoFocus disabled={isDeleting} onClick={onClose} type="button" variant="outline">Cancelar</Button>
        <Button disabled={isDeleting} onClick={confirmDelete} type="button" variant="destructive">
          {isDeleting ? <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> : <Trash2 aria-hidden="true" className="h-4 w-4" />}
          {isDeleting ? "Excluindo…" : "Excluir definitivamente"}
        </Button>
      </div>
    </dialog>
  );
}
