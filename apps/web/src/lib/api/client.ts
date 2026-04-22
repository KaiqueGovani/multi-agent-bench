import type {
  ConversationDetailResponse,
  CreateConversationResponse,
  MessageListResponse,
  ProcessingEvent,
  SendMessageResponse
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers
    }
  });

  if (!response.ok) {
    const detail = await readError(response);
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? "";
  } catch {
    return "";
  }
}

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

export function getAttachmentUrl(attachmentId: string): string {
  return `${API_BASE_URL}/attachments/${attachmentId}`;
}

export function createConversation(): Promise<CreateConversationResponse> {
  return request<CreateConversationResponse>("/conversations", {
    method: "POST",
    body: JSON.stringify({
      channel: "web_chat",
      userSessionId: getLocalSessionId(),
      metadata: getClientMetadata()
    })
  });
}

export function getConversation(conversationId: string): Promise<ConversationDetailResponse> {
  return request<ConversationDetailResponse>(`/conversations/${conversationId}`);
}

export function getConversationMessages(conversationId: string): Promise<MessageListResponse> {
  return request<MessageListResponse>(`/conversations/${conversationId}/messages`);
}

export function getConversationEvents(conversationId: string): Promise<ProcessingEvent[]> {
  return request<ProcessingEvent[]>(`/conversations/${conversationId}/events`);
}

export function sendMessage(
  conversationId: string,
  text: string,
  files: File[] = []
): Promise<SendMessageResponse> {
  const body = new FormData();
  body.append("conversationId", conversationId);
  if (text.trim()) {
    body.append("text", text);
  }
  body.append(
    "metadata_json",
    JSON.stringify({
      ...getClientMetadata(),
      fileCount: files.length,
      fileTypes: files.map((file) => file.type),
      fileSizes: files.map((file) => file.size)
    })
  );
  for (const file of files) {
    body.append("files", file);
  }

  return request<SendMessageResponse>("/messages", {
    method: "POST",
    body
  });
}

function getClientMetadata() {
  return {
    clientTimestamp: new Date().toISOString(),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    locale: navigator.language,
    userAgent: navigator.userAgent,
    deviceType: window.innerWidth < 768 ? "mobile" : "desktop",
    channel: "web_chat",
    runtimeMode: "mock",
    architectureMode: "centralized_orchestration"
  };
}

function getLocalSessionId(): string {
  const key = "multi-agent-bench.session-id";
  const existing = window.localStorage.getItem(key);
  if (existing) {
    return existing;
  }
  const next = crypto.randomUUID();
  window.localStorage.setItem(key, next);
  return next;
}
