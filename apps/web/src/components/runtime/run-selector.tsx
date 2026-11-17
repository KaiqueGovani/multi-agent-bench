"use client";

import { History } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatArchitectureLabel, formatStatusLabel } from "@/components/runtime/presentation";
import type { Message, Run } from "@/lib/types";

export function RunSelector({ runs, messages, selectedRun, isFollowingLatest, onSelect, onFollowLatest }: {
  runs: Run[];
  messages: Message[];
  selectedRun: Run;
  isFollowingLatest: boolean;
  onSelect: (id: string) => void;
  onFollowLatest: () => void;
}) {
  const ordered = [...runs].sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime() || a.id.localeCompare(b.id));
  const groups = new Map<string, Run[]>();
  for (const run of ordered) {
    const key = run.messageId || run.id;
    groups.set(key, [...(groups.get(key) ?? []), run]);
  }
  const entries = [...groups.entries()];
  const message = messages.find((item) => item.id === selectedRun.messageId);
  const ordinal = entries.findIndex(([id]) => id === (selectedRun.messageId || selectedRun.id)) + 1;

  return (
    <section aria-label="Seleção de execução" className="min-w-0 border-b bg-card/60 px-3 py-2 sm:px-4" data-testid="run-selector">
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <label className="flex shrink-0 items-center gap-1.5 text-xs font-medium" htmlFor="selected-conversation-run">
          <History aria-hidden="true" className="h-3.5 w-3.5 text-muted-foreground" />Execução
        </label>
        <select
          className="h-9 min-w-0 flex-1 rounded-md border bg-background px-2 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:max-w-xl"
          id="selected-conversation-run"
          onChange={(event) => onSelect(event.target.value)}
          value={selectedRun.id}
        >
          {entries.map(([id, group], index) => (
            <optgroup key={id} label={`Mensagem ${index + 1}`}>
              {group.map((run) => (
                <option key={run.id} value={run.id}>
                  Mensagem {index + 1} · {formatArchitectureLabel(String(run.experiment?.architectureKey ?? "centralized_orchestration"))} · {formatStatusLabel(run.status)} · {run.id.slice(0, 8)}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
        <Button aria-pressed={isFollowingLatest} className="h-9 text-xs" onClick={onFollowLatest} size="sm" type="button" variant={isFollowingLatest ? "secondary" : "outline"}>
          Mais recente
        </Button>
      </div>
      <p className="mt-1.5 line-clamp-2 break-words text-xs leading-relaxed text-muted-foreground">
        Mensagem {ordinal}{message?.contentText ? `: ${message.contentText}` : " · Mensagem com anexos"}
        <span className="ml-1">· O fluxo e a visão geral acompanham esta execução.</span>
      </p>
    </section>
  );
}
