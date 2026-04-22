import type {
  ArchitectureMode,
  AttachmentStatus,
  ChannelType,
  ConversationStatus,
  MessageDirection,
  MessageStatus,
  ProcessingEventType,
  ProcessingStatus,
  ReviewTaskStatus,
  RuntimeMode,
} from "./enums";

export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
export type JsonObject = { [key: string]: JsonValue };

export type IsoDateTime = string;
export type Uuid = string;

export interface ModelContext {
  language?: string;
  currentTime?: IsoDateTime;
  conversationSummary?: string;
  attachmentTypes?: string[];
  inferredIntent?: string;
}

export interface OperationalMetadata {
  requestId?: Uuid;
  correlationId?: Uuid;
  clientTimestamp?: IsoDateTime;
  timezone?: string;
  locale?: string;
  userAgent?: string;
  deviceType?: string;
  uploadDurationMs?: number;
  messageInputDurationMs?: number;
  fileCount?: number;
  fileTypes?: string[];
  fileSizes?: number[];
  processingStartAt?: IsoDateTime;
  processingEndAt?: IsoDateTime;
  totalDurationMs?: number;
  stepDurationMs?: number;
  channel?: ChannelType;
  architectureMode?: ArchitectureMode;
  runtimeMode?: RuntimeMode;
  reviewRequired?: boolean;
  [key: string]: JsonValue | undefined;
}

export interface Conversation {
  id: Uuid;
  channel: ChannelType;
  createdAt: IsoDateTime;
  updatedAt: IsoDateTime;
  status: ConversationStatus;
  userSessionId?: string;
  metadata: OperationalMetadata;
}

export interface Message {
  id: Uuid;
  conversationId: Uuid;
  direction: MessageDirection;
  contentText?: string;
  createdAtClient?: IsoDateTime;
  createdAtServer: IsoDateTime;
  status: MessageStatus;
  correlationId: Uuid;
  metadata: OperationalMetadata;
  modelContext?: ModelContext;
}

export interface Attachment {
  id: Uuid;
  messageId: Uuid;
  storageKey: string;
  originalFilename: string;
  mimeType: string;
  sizeBytes: number;
  checksum: string;
  width?: number;
  height?: number;
  createdAt: IsoDateTime;
  status: AttachmentStatus;
  metadata: OperationalMetadata;
}

export interface ProcessingEvent {
  id: Uuid;
  conversationId: Uuid;
  messageId?: Uuid;
  eventType: ProcessingEventType;
  actorName?: string;
  parentEventId?: Uuid;
  correlationId: Uuid;
  payload: JsonObject;
  createdAt: IsoDateTime;
  durationMs?: number;
  status: ProcessingStatus;
}

export interface ReviewTask {
  id: Uuid;
  conversationId: Uuid;
  messageId: Uuid;
  reason: string;
  status: ReviewTaskStatus;
  createdAt: IsoDateTime;
  resolvedAt?: IsoDateTime;
  metadata: OperationalMetadata;
}

export interface NormalizedAttachmentInput {
  clientAttachmentId?: string;
  originalFilename: string;
  mimeType: string;
  sizeBytes: number;
  checksum?: string;
  width?: number;
  height?: number;
  metadata: OperationalMetadata;
}

export interface NormalizedInboundMessage {
  channel: ChannelType;
  conversationId?: Uuid;
  clientMessageId?: string;
  userSessionId?: string;
  text?: string;
  attachments: NormalizedAttachmentInput[];
  createdAtClient?: IsoDateTime;
  metadata: OperationalMetadata;
  modelContext?: ModelContext;
}

export interface NormalizedOutboundMessage {
  channel: ChannelType;
  conversationId: Uuid;
  messageId: Uuid;
  correlationId: Uuid;
  text: string;
  attachments: Attachment[];
  status: MessageStatus;
  metadata: OperationalMetadata;
  modelContext?: ModelContext;
}

