import { appendApiKeyQuery, getApiBaseUrl } from "@/lib/api/client";
import type { ProcessingEvent, RunExecutionEvent } from "@/lib/types";

export function openConversationEventStream(
  conversationId: string,
  onEvent: (event: ProcessingEvent) => void,
  onConnectionChange?: (status: "connecting" | "open" | "closed" | "error" | "reconnecting") => void,
  options: { lastEventId?: string | null } = {}
): EventSource {
  onConnectionChange?.("connecting");
  const url = new URL(`${getApiBaseUrl()}/conversations/${conversationId}/events/stream`);
  if (options.lastEventId) {
    url.searchParams.set("lastEventId", options.lastEventId);
  }
  appendApiKeyQuery(url);
  const source = new EventSource(url.toString());

  source.onopen = () => onConnectionChange?.("open");
  source.onerror = () => onConnectionChange?.("reconnecting");

  source.addEventListener("processing.event", (message) => {
    onEvent(JSON.parse(message.data) as ProcessingEvent);
  });

  source.addEventListener("heartbeat", () => {
    onConnectionChange?.("open");
  });

  return source;
}

export function openRunExecutionStream(
  runId: string,
  onEvent: (event: RunExecutionEvent) => void,
  onConnectionChange?: (status: "connecting" | "open" | "closed" | "error" | "reconnecting") => void,
  options: { lastSequenceNo?: number } = {}
): EventSource {
  onConnectionChange?.("connecting");
  const url = new URL(`${getApiBaseUrl()}/runs/${runId}/execution/stream`);
  if (typeof options.lastSequenceNo === "number" && options.lastSequenceNo > 0) {
    url.searchParams.set("lastSequenceNo", String(options.lastSequenceNo));
  }
  appendApiKeyQuery(url);
  const source = new EventSource(url.toString());

  source.onopen = () => onConnectionChange?.("open");
  source.onerror = () => onConnectionChange?.("reconnecting");

  source.addEventListener("run.execution", (message) => {
    onEvent(JSON.parse(message.data) as RunExecutionEvent);
  });

  source.addEventListener("heartbeat", () => {
    onConnectionChange?.("open");
  });

  return source;
}
