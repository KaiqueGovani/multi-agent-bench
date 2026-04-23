import type {
  ArchitectureMode,
  ConversationListResponse,
  ConversationDetailResponse,
  CreateConversationResponse,
  MessageListResponse,
  ProcessingEvent,
  ResolveReviewTaskRequest,
  ReviewTask,
  ReviewTaskListResponse,
  SendMessageResponse
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        ...getApiKeyHeaders(),
        ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...init?.headers
      }
    });
  } catch {
    throw new Error(
      `Could not reach API at ${API_BASE_URL}. Check that the API is running and CORS allows this web origin.`
    );
  }

  if (!response.ok) {
    const detail = await readError(response);
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    if (body.detail) {
      return `${body.detail} (HTTP ${response.status})`;
    }
  } catch {
    // Fall through to the generic status message.
  }
  return `Request failed with status ${response.status}`;
}

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

export function getApiKey(): string {
  return API_KEY;
}

export function getAttachmentUrl(attachmentId: string): string {
  const url = new URL(`${API_BASE_URL}/attachments/${attachmentId}`);
  appendApiKeyQuery(url);
  return url.toString();
}

export function createConversation(
  architectureMode: ArchitectureMode
): Promise<CreateConversationResponse> {
  return request<CreateConversationResponse>("/conversations", {
    method: "POST",
    body: JSON.stringify({
      channel: "web_chat",
      userSessionId: getLocalSessionId(),
      metadata: getClientMetadata(architectureMode)
    })
  });
}

export function listConversations(): Promise<ConversationListResponse> {
  return request<ConversationListResponse>("/conversations");
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

export function listOpenReviewTasks(): Promise<ReviewTaskListResponse> {
  return request<ReviewTaskListResponse>("/reviews");
}

export function resolveReviewTask(
  reviewTaskId: string,
  payload: ResolveReviewTaskRequest
): Promise<ReviewTask> {
  return request<ReviewTask>(`/reviews/${reviewTaskId}/resolve`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function sendMessage(
  conversationId: string,
  text: string,
  files: File[],
  architectureMode: ArchitectureMode
): Promise<SendMessageResponse> {
  const body = new FormData();
  body.append("conversationId", conversationId);
  if (text.trim()) {
    body.append("text", text);
  }
  body.append(
    "metadata_json",
    JSON.stringify({
      ...getClientMetadata(architectureMode),
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

function getClientMetadata(architectureMode: ArchitectureMode) {
  return {
    clientTimestamp: new Date().toISOString(),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    locale: navigator.language,
    userAgent: navigator.userAgent,
    deviceType: window.innerWidth < 768 ? "mobile" : "desktop",
    channel: "web_chat",
    runtimeMode: "mock",
    architectureMode
  };
}

function getApiKeyHeaders(): HeadersInit {
  return API_KEY ? { "X-API-Key": API_KEY } : {};
}

export function appendApiKeyQuery(url: URL): void {
  if (API_KEY) {
    url.searchParams.set("apiKey", API_KEY);
  }
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
