import type {
  Attachment,
  Conversation,
  DashboardConversationItem,
  DashboardDistributionItem,
  DashboardTotals,
  IsoDateTime,
  JsonObject,
  Message,
  NormalizedInboundMessage,
  ProcessingEvent,
  ReviewTask,
  Run,
  RunExecutionDetail,
  RunExecutionEvent,
  RunExecutionProjection,
  RunExperimentMetadata,
  RuntimeDispatchRequest,
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

export interface ConversationSummary {
  conversationId: Uuid;
  status: Conversation["status"];
  channel: ChannelType;
  architectureMode?: string;
  updatedAt: IsoDateTime;
  lastMessage?: string;
  messageCount: number;
  eventCount: number;
  latestRunId?: Uuid;
  reviewPending: boolean;
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
}

export interface DashboardMetricsResponse {
  generatedAt: IsoDateTime;
  totals: DashboardTotals;
  byArchitecture: DashboardDistributionItem[];
  byModel: DashboardDistributionItem[];
  byScenario: DashboardDistributionItem[];
  byAttachmentType: DashboardDistributionItem[];
  conversations: DashboardConversationItem[];
}

export interface ReviewTaskListResponse {
  reviewTasks: ReviewTask[];
}

export interface ResolveReviewTaskRequest {
  status: "resolved" | "cancelled" | "in_review";
  note?: string;
  resolvedBy?: string;
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
  runId?: Uuid;
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

export interface IngestProcessingEventRequest {
  conversationId: Uuid;
  messageId?: Uuid;
  runId?: Uuid;
  eventType: ProcessingEvent["eventType"];
  actorName?: string;
  parentEventId?: Uuid;
  correlationId: Uuid;
  payload?: JsonObject;
  durationMs?: number;
  status: ProcessingStatus;
  externalEventId?: string;
  source?: "mock_runtime" | "ai_service" | "system";
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

export interface IngestRunExecutionEventRequest {
  runId: Uuid;
  conversationId: Uuid;
  messageId: Uuid;
  correlationId: Uuid;
  eventFamily: RunExecutionEvent["eventFamily"];
  eventName: string;
  status: ProcessingStatus;
  actorName?: string;
  nodeId?: string;
  toolName?: string;
  source?: string;
  durationMs?: number;
  externalEventId?: string;
  payload?: JsonObject;
}

export interface RunExecutionStreamEvent {
  eventId: Uuid;
  runId: Uuid;
  eventFamily: RunExecutionEvent["eventFamily"];
  eventName: string;
  sequenceNo: number;
  status: ProcessingStatus;
  createdAt: IsoDateTime;
  actorName?: string;
  nodeId?: string;
  toolName?: string;
  source?: string;
  durationMs?: number;
  payload: JsonObject;
}

export interface RunComparisonContextResponse {
  run: Run;
  peerRuns: Run[];
  architectureDistribution: DashboardDistributionItem[];
  scenarioDistribution: DashboardDistributionItem[];
}

export interface MessageListResponse {
  conversationId: Uuid;
  messages: Message[];
  attachments: Attachment[];
}

export interface RuntimeDispatchResponse {
  accepted: boolean;
  runId: Uuid;
  status: "accepted";
}

export interface RunExecutionResponse {
  run: Run;
  projection?: RunExecutionProjection;
  executionEvents: RunExecutionEvent[];
}

export interface RunExecutionProjectionResponse {
  projection?: RunExecutionProjection;
}

export interface RuntimeDispatchEnvelope {
  dispatchedAt: IsoDateTime;
  request: RuntimeDispatchRequest;
}

export interface NormalizedInboundEnvelope {
  requestId: Uuid;
  receivedAt: IsoDateTime;
  message: NormalizedInboundMessage;
}
