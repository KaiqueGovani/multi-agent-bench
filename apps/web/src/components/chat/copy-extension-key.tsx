"use client";

import { Check, Copy } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { getApiKey } from "@/lib/api/client";

export function CopyExtensionKey() {
  const key = getApiKey();
  const timerRef = useRef<number | undefined>(undefined);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => () => { window.clearTimeout(timerRef.current); }, []);

  async function copyKey() {
    if (!key) return;
    setError(false);
    try {
      await navigator.clipboard.writeText(key);
      setCopied(true);
      window.clearTimeout(timerRef.current);
      timerRef.current = window.setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopied(false);
      setError(true);
    }
  }

  return (
    <>
      <Button
        aria-label="Copiar chave da extensão"
        className="h-9 w-9 shrink-0"
        disabled={!key}
        onClick={copyKey}
        size="icon"
        title="Copiar chave da API do MAB para a extensão"
        type="button"
        variant="ghost"
      >
        {copied ? <Check aria-hidden="true" className="h-4 w-4 text-emerald-700" /> : <Copy aria-hidden="true" className="h-4 w-4 text-muted-foreground" />}
      </Button>
      {copied ? (
        <p className="fixed bottom-4 right-4 z-50 max-w-[calc(100vw_-_2rem)] rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-950 shadow-sm" role="status">
          Chave da extensão copiada.
        </p>
      ) : null}
      {error ? (
        <p className="fixed bottom-4 right-4 z-50 max-w-[calc(100vw_-_2rem)] rounded-lg border border-destructive/40 bg-card px-3 py-2 text-sm text-destructive shadow-sm" role="alert">
          Não foi possível copiar a chave. Permita o acesso à área de transferência e tente novamente.
        </p>
      ) : null}
    </>
  );
}
