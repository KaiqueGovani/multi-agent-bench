import { getApiBaseUrl } from "@/lib/api/client";
import type { ProcessingEvent } from "@/lib/types";

export function openConversationEventStream(
  conversationId: string,
  onEvent: (event: ProcessingEvent) => void,
  onConnectionChange?: (status: "connecting" | "open" | "closed" | "error") => void
): EventSource {
  onConnectionChange?.("connecting");
  const source = new EventSource(
    `${getApiBaseUrl()}/conversations/${conversationId}/events/stream`
  );

  source.onopen = () => onConnectionChange?.("open");
  source.onerror = () => onConnectionChange?.("error");

  source.addEventListener("processing.event", (message) => {
    onEvent(JSON.parse(message.data) as ProcessingEvent);
  });

  source.addEventListener("heartbeat", () => {
    onConnectionChange?.("open");
  });

  return source;
}

