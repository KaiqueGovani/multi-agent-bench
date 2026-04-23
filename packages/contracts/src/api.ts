import type {
  Attachment,
  Conversation,
  IsoDateTime,
  JsonObject,
  Message,
  NormalizedInboundMessage,
  ProcessingEvent,
  ReviewTask,
  Run,
  RunExperimentMetadata,
  RunSummary,
  Uuid,
} from "./domain";
import type {
  ChannelType,
  MessageStatus,
  ProcessingStatus,
  RunStatus,
} from "./enums";

export interface CreateConversationRequest {
  channel: ChannelType;
  userSessionId?: string;
  metadata?: JsonObject;
}

export interface CreateConversationResponse {
  conversationId: Uuid;
  status: Conversation["status"];
  channel: ChannelType;
  createdAt: IsoDateTime;
}

export interface ConversationDetailResponse {
  conversation: Conversation;
  messages: Message[];
  attachments: Attachment[];
  runs: Run[];
  events: ProcessingEvent[];
  reviewTasks: ReviewTask[];
}

export interface SendMessageMultipartFields {
  conversationId?: Uuid;
  text?: string;
  metadataJson: JsonObject;
  clientMessageId?: string;
}

export interface SendMessageResponse {
  messageId: Uuid;
  conversationId: Uuid;
  status: MessageStatus;
  correlationId: Uuid;
  acceptedAt: IsoDateTime;
}

export interface SseProcessingEvent {
  eventId: Uuid;
  eventType: ProcessingEvent["eventType"];
  actorName?: string;
  messageId?: Uuid;
  conversationId: Uuid;
  correlationId: Uuid;
  status: ProcessingStatus;
  createdAt: IsoDateTime;
  durationMs?: number;
  payload: JsonObject;
}

export interface CreateRunRequest {
  conversationId: Uuid;
  messageId: Uuid;
  correlationId: Uuid;
  aiSessionId?: string;
  traceparent?: string;
  experiment: RunExperimentMetadata;
}

export interface CreateRunResponse {
  runId: Uuid;
  conversationId: Uuid;
  messageId: Uuid;
  status: RunStatus;
  aiSessionId?: string;
  createdAt: IsoDateTime;
}

export interface CompleteRunRequest {
  status: RunStatus;
  externalRunId?: string;
  traceId?: string;
  finishedAt?: IsoDateTime;
  totalDurationMs?: number;
  humanReviewRequired?: boolean;
  finalOutcome?: string;
  summary?: RunSummary;
}

export interface MessageListResponse {
  conversationId: Uuid;
  messages: Message[];
  attachments: Attachment[];
}

export interface NormalizedInboundEnvelope {
  requestId: Uuid;
  receivedAt: IsoDateTime;
  message: NormalizedInboundMessage;
}
