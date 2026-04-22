export type ChannelType = "web_chat" | "whatsapp";

export type ConversationStatus =
  | "active"
  | "waiting"
  | "completed"
  | "error"
  | "human_review_required";

export type MessageDirection = "inbound" | "outbound" | "system";

export type MessageStatus =
  | "draft"
  | "received"
  | "accepted"
  | "validating"
  | "processing"
  | "forwarded"
  | "waiting"
  | "completed"
  | "error"
  | "human_review_required";

export type ProcessingEventType =
  | "conversation.created"
  | "message.received"
  | "attachment.upload.started"
  | "attachment.upload.completed"
  | "attachment.validation.started"
  | "attachment.validation.completed"
  | "processing.started"
  | "actor.invoked"
  | "actor.progress"
  | "actor.completed"
  | "actor.failed"
  | "handoff.requested"
  | "review.required"
  | "response.partial"
  | "response.final"
  | "processing.completed";

export type ProcessingStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "waiting"
  | "human_review_required";

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type JsonObject = { [key: string]: JsonValue };

export interface Conversation {
  id: string;
  channel: ChannelType;
  createdAt: string;
  updatedAt: string;
  status: ConversationStatus;
  userSessionId?: string | null;
  metadata: JsonObject;
}

export interface Message {
  id: string;
  conversationId: string;
  direction: MessageDirection;
  contentText?: string | null;
  createdAtClient?: string | null;
  createdAtServer: string;
  status: MessageStatus;
  correlationId: string;
  metadata: JsonObject;
}

export interface Attachment {
  id: string;
  messageId: string;
  storageKey: string;
  originalFilename: string;
  mimeType: string;
  sizeBytes: number;
  checksum: string;
  width?: number | null;
  height?: number | null;
  createdAt: string;
  status: string;
  metadata: JsonObject;
}

export interface ProcessingEvent {
  id: string;
  conversationId: string;
  messageId?: string | null;
  eventType: ProcessingEventType;
  actorName?: string | null;
  parentEventId?: string | null;
  correlationId: string;
  payload: JsonObject;
  createdAt: string;
  durationMs?: number | null;
  status: ProcessingStatus;
}

export interface CreateConversationResponse {
  conversationId: string;
  status: ConversationStatus;
  channel: ChannelType;
  createdAt: string;
}

export interface SendMessageResponse {
  messageId: string;
  conversationId: string;
  status: MessageStatus;
  correlationId: string;
  acceptedAt: string;
}

export interface ConversationDetailResponse {
  conversation: Conversation;
  messages: Message[];
  attachments: Attachment[];
  events: ProcessingEvent[];
  reviewTasks: unknown[];
}

export interface MessageListResponse {
  conversationId: string;
  messages: Message[];
  attachments: Attachment[];
}

