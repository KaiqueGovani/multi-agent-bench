import { getApiBaseUrl } from "@/lib/api/client";
import type { ProcessingEvent } from "@/lib/types";

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
