"use client";

import { Eye, EyeOff, KeyRound, Loader2, X } from "lucide-react";
import { useRef, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getAvailableModels, getLlmSettings, updateLlmSettings } from "@/lib/api/client";
import type { AvailableModel, ModelProvider, RuntimeHealthStatus } from "@/lib/types";

const defaultModels: Record<ModelProvider, string> = {
  bedrock: "us.anthropic.claude-haiku-4-5-20251001-v1:0",
  anthropic: "claude-haiku-4-5-20251001",
};

function providerLabel(provider?: ModelProvider) {
  return provider === "anthropic" ? "Anthropic" : "Amazon Bedrock";
}

export function LlmSettings({
  onStatusChange,
  runtimeStatus,
}: {
  onStatusChange: (status: RuntimeHealthStatus) => void;
  runtimeStatus: RuntimeHealthStatus | null;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const savingRef = useRef(false);
  const generationRef = useRef(0);
  const modelRequestRef = useRef(0);
  const [settingsStatus, setSettingsStatus] = useState<RuntimeHealthStatus | null>(null);
  const [provider, setProvider] = useState<ModelProvider>("bedrock");
  const [models, setModels] = useState(defaultModels);
  const [availableModels, setAvailableModels] = useState<Record<ModelProvider, AvailableModel[]>>({ bedrock: [], anthropic: [] });
  const [modelSources, setModelSources] = useState<Partial<Record<ModelProvider, "provider" | "catalog">>>({});
  const [customModels, setCustomModels] = useState<Record<ModelProvider, boolean>>({ bedrock: false, anthropic: false });
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  function clearDraft() {
    setApiKey("");
    setShowKey(false);
    setError(null);
    setSaved(false);
  }

  function loadStatus(status: RuntimeHealthStatus | null) {
    setSettingsStatus(status);
    const active = status?.llm?.provider ?? "bedrock";
    setProvider(active);
    setModels({ ...defaultModels, ...status?.llm?.models, ...(status?.llm?.modelId ? { [active]: status.llm.modelId } : {}) });
    setCustomModels({ bedrock: false, anthropic: false });
  }

  async function openSettings() {
    clearDraft();
    loadStatus(runtimeStatus);
    const generation = ++generationRef.current;
    setIsLoading(true);
    dialogRef.current?.showModal();
    try {
      const status = await getLlmSettings();
      if (generation !== generationRef.current) return;
      loadStatus(status);
      onStatusChange(status);
    } catch (failure) {
      if (generation === generationRef.current) {
        setError(failure instanceof Error ? failure.message : "Não foi possível consultar a configuração atual.");
      }
    } finally {
      if (generation === generationRef.current) setIsLoading(false);
    }
  }

  function closeSettings() {
    if (savingRef.current) return;
    generationRef.current += 1;
    modelRequestRef.current += 1;
    dialogRef.current?.close();
    setIsLoading(false);
    setIsLoadingModels(false);
    clearDraft();
  }

  async function applyKey(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (savingRef.current || isLoading || isLoadingModels) return;
    const nextKey = apiKey.trim();
    if ((!nextKey && !hasKey) || /\s|[\x00-\x1f\x7f]/u.test(nextKey)) {
      setError("Cole uma chave válida, sem espaços ou quebras de linha.");
      return;
    }
    savingRef.current = true;
    setIsSaving(true);
    setError(null);
    setSaved(false);
    try {
      const status = await updateLlmSettings({ provider, modelId: models[provider].trim(), ...(nextKey ? { apiKey: nextKey } : {}) });
      onStatusChange(status);
      loadStatus(status);
      setApiKey("");
      setShowKey(false);
      setSaved(true);
      inputRef.current?.focus();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Não foi possível atualizar a configuração. Tente novamente.");
    } finally {
      savingRef.current = false;
      setIsSaving(false);
    }
  }

  async function loadModels() {
    if (isLoadingModels || isLoading || savingRef.current) return;
    const key = apiKey.trim();
    if (/\s|[\x00-\x1f\x7f]/u.test(key)) {
      setError("Cole uma chave válida, sem espaços ou quebras de linha.");
      return;
    }
    const request = ++modelRequestRef.current;
    const generation = generationRef.current;
    setIsLoadingModels(true);
    setError(null);
    setSaved(false);
    try {
      const response = await getAvailableModels({ provider, ...(key ? { apiKey: key } : {}) });
      if (request !== modelRequestRef.current || generation !== generationRef.current) return;
      setAvailableModels((current) => ({ ...current, [provider]: response.models }));
      setModelSources((current) => ({ ...current, [provider]: response.source }));
    } catch (failure) {
      if (request === modelRequestRef.current && generation === generationRef.current) {
        setError(failure instanceof Error ? failure.message : "Não foi possível carregar os modelos. Verifique sua chave e tente novamente.");
      }
    } finally {
      if (request === modelRequestRef.current && generation === generationRef.current) setIsLoadingModels(false);
    }
  }

  const llm = settingsStatus?.llm;
  const hasKey = llm?.credentialsConfigured?.[provider] ?? ((llm?.provider ?? "bedrock") === provider && Boolean(llm?.tokenConfigured));
  const disabled = isSaving || isLoading || isLoadingModels;
  const modelOptions = [...availableModels[provider]];
  if (models[provider] && !modelOptions.some((model) => model.id === models[provider])) {
    modelOptions.unshift({ id: models[provider], name: models[provider] });
  }

  return (
    <>
      <Button
        aria-label="Configurar provedor de IA"
        aria-haspopup="dialog"
        onClick={openSettings}
        size="sm"
        type="button"
        variant="outline"
      >
        <KeyRound aria-hidden="true" className="h-4 w-4" />
        <span>{runtimeStatus?.llm?.provider === "anthropic" ? "Anthropic" : "Bedrock"}</span>
      </Button>
      <dialog
        aria-describedby="llm-settings-description"
        aria-labelledby="llm-settings-title"
        className="fixed inset-0 m-auto max-h-[calc(100dvh_-_2rem)] w-[calc(100%_-_2rem)] max-w-lg overflow-y-auto rounded-xl border bg-card p-0 text-card-foreground shadow-xl backdrop:bg-black/50"
        onCancel={(event) => {
          event.preventDefault();
          closeSettings();
        }}
        onClose={clearDraft}
        ref={dialogRef}
      >
        <div className="flex items-center justify-between gap-3 border-b px-5 py-4">
          <h2 className="text-base font-semibold" id="llm-settings-title">Provedor de IA</h2>
          <Button
            aria-label="Fechar configurações de IA"
            disabled={isSaving}
            onClick={closeSettings}
            size="icon"
            type="button"
            variant="ghost"
          >
            <X aria-hidden="true" className="h-4 w-4" />
          </Button>
        </div>
        <form className="grid gap-4 p-5" onSubmit={applyKey}>
          <p className="text-sm text-muted-foreground" id="llm-settings-description">
            Escolha o provedor, o modelo e a chave sem reiniciar a aplicação. A alteração vale para as próximas execuções, inclusive pelo WhatsApp.
          </p>
          {isLoading ? <p className="text-sm text-muted-foreground" role="status">Consultando configuração…</p> : null}
          <div className="grid gap-2">
            <label className="text-sm font-medium" htmlFor="llm-provider">Provedor</label>
            <select
              className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
              disabled={disabled}
              id="llm-provider"
              onChange={(event) => {
                setProvider(event.target.value as ModelProvider);
                clearDraft();
              }}
              value={provider}
            >
              <option value="bedrock">Amazon Bedrock</option>
              <option value="anthropic">Anthropic (Claude)</option>
            </select>
            <p className="text-xs text-muted-foreground">{provider === "anthropic" ? "Conexão direta à API Anthropic, usando uma chave Anthropic." : "Conexão via AWS, usando uma chave de API Bedrock."}</p>
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium" htmlFor="llm-model">Modelo</label>
            <select
              className="h-10 w-full min-w-0 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
              disabled={disabled}
              id="llm-model"
              onChange={(event) => {
                const value = event.target.value;
                setCustomModels((current) => ({ ...current, [provider]: value === "__custom__" }));
                if (value !== "__custom__") setModels((current) => ({ ...current, [provider]: value }));
                setSaved(false);
                setError(null);
              }}
              value={customModels[provider] ? "__custom__" : models[provider]}
            >
              {modelOptions.map((model) => <option key={model.id} value={model.id}>{model.name}</option>)}
              <option value="__custom__">Outro modelo…</option>
            </select>
            {customModels[provider] ? (
              <>
                <label className="text-sm font-medium" htmlFor="llm-custom-model">Identificador do modelo</label>
                <Input
                  disabled={disabled}
                  id="llm-custom-model"
                  maxLength={512}
                  onChange={(event) => {
                    setModels((current) => ({ ...current, [provider]: event.target.value }));
                    setSaved(false);
                    setError(null);
                  }}
                  placeholder={defaultModels[provider]}
                  value={models[provider]}
                />
              </>
            ) : null}
            <Button
              className="justify-self-start"
              disabled={disabled || (provider === "anthropic" && !apiKey.trim() && !hasKey)}
              onClick={loadModels}
              size="sm"
              type="button"
              variant="outline"
            >
              {isLoadingModels ? <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> : null}
              {isLoadingModels ? "Carregando modelos…" : "Carregar modelos"}
            </Button>
            <p className="text-xs text-muted-foreground">
              {modelSources[provider] === "catalog"
                ? "Catálogo de modelos. A disponibilidade depende do acesso da sua conta e da região."
                : modelSources[provider] === "provider"
                  ? "Modelos retornados pelo provedor. A lista não altera sua configuração."
                  : provider === "anthropic"
                    ? "Cole sua chave Anthropic abaixo e carregue os modelos disponíveis."
                    : "Carregue os modelos ou use um identificador personalizado."}
            </p>
          </div>
          <p className="text-sm">
            Chave para {providerLabel(provider)}: <span className="font-medium">{llm ? hasKey ? "configurada" : "não configurada" : "status indisponível"}</span>
          </p>
          <div className="grid gap-2">
            <label className="text-sm font-medium" htmlFor="llm-api-key">Nova chave de API</label>
            <div className="flex items-center gap-2">
              <Input
                aria-describedby="llm-key-storage"
                autoCapitalize="none"
                autoComplete="off"
                className="min-w-0 flex-1"
                disabled={disabled}
                id="llm-api-key"
                maxLength={16384}
                onChange={(event) => {
                  setApiKey(event.target.value);
                  setError(null);
                  setSaved(false);
                }}
                placeholder={hasKey ? "Deixe vazio para manter a chave atual" : `Cole a chave ${provider === "anthropic" ? "Anthropic" : "Bedrock"}`}
                ref={inputRef}
                spellCheck={false}
                type={showKey ? "text" : "password"}
                value={apiKey}
              />
              <Button
                aria-label={showKey ? "Ocultar chave" : "Mostrar chave"}
                aria-pressed={showKey}
                disabled={disabled}
                onClick={() => setShowKey((current) => !current)}
                size="icon"
                type="button"
                variant="outline"
              >
                {showKey ? <EyeOff aria-hidden="true" className="h-4 w-4" /> : <Eye aria-hidden="true" className="h-4 w-4" />}
              </Button>
            </div>
            <p className="text-xs leading-relaxed text-muted-foreground" id="llm-key-storage">
              {hasKey ? "Deixe a chave vazia para reutilizar a já configurada. " : ""}As chaves ficam apenas na memória do servidor até ele reiniciar. Elas não são salvas no navegador. A validade será confirmada na próxima chamada ao provedor.
            </p>
          </div>
          {saved ? (
            <p className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900" role="status">
              Configuração atualizada. As próximas execuções usarão o provedor e o modelo selecionados.
            </p>
          ) : null}
          {saved && llm && !llm.enabled ? (
            <p className="text-sm text-amber-800">O modo real está desativado no servidor. Ative-o para usar o provedor.</p>
          ) : saved && llm && !llm.sdkAvailable ? (
            <p className="text-sm text-amber-800">O serviço de execução ainda precisa das dependências deste provedor para usar o modo real.</p>
          ) : null}
          {error ? <p className="rounded-md border border-destructive/40 p-3 text-sm text-destructive" role="alert">{error}</p> : null}
          <div className="flex justify-end">
            <Button disabled={disabled || !models[provider].trim() || (!apiKey.trim() && !hasKey)} type="submit">
              {isSaving ? <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> : <KeyRound aria-hidden="true" className="h-4 w-4" />}
              {isSaving ? "Aplicando…" : "Aplicar configuração"}
            </Button>
          </div>
        </form>
      </dialog>
    </>
  );
}
