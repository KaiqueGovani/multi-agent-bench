export type ChannelType = "web_chat" | "whatsapp";

export type ArchitectureMode =
  | "centralized_orchestration"
  | "structured_workflow"
  | "decentralized_swarm";

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

export type RunStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "human_review_required";

export type ReviewTaskStatus = "open" | "in_review" | "resolved" | "cancelled";

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

export interface Run {
  id: string;
  conversationId: string;
  messageId: string;
  correlationId: string;
  externalRunId?: string | null;
  aiSessionId?: string | null;
  traceId?: string | null;
  status: RunStatus;
  startedAt?: string | null;
  finishedAt?: string | null;
  totalDurationMs?: number | null;
  humanReviewRequired?: boolean | null;
  finalOutcome?: string | null;
  experiment: JsonObject;
  summary: JsonObject;
  createdAt: string;
  updatedAt: string;
}

export interface RunExecutionEvent {
  id: string;
  runId: string;
  conversationId: string;
  messageId: string;
  correlationId: string;
  eventFamily: string;
  eventName: string;
  sequenceNo: number;
  createdAt: string;
  status: ProcessingStatus;
  actorName?: string | null;
  nodeId?: string | null;
  toolName?: string | null;
  source?: string | null;
  externalEventId?: string | null;
  durationMs?: number | null;
  payload: JsonObject;
}

export interface RunExecutionProjection {
  runId: string;
  conversationId: string;
  messageId: string;
  architectureMode: string;
  runStatus: RunStatus;
  activeNodeId?: string | null;
  activeActorName?: string | null;
  currentPhase?: string | null;
  source?: string | null;
  architectureView: JsonObject;
  metrics: JsonObject;
  state: JsonObject;
  updatedAt: string;
}

export interface RunExecutionResponse {
  run: Run;
  projection?: RunExecutionProjection | null;
  executionEvents: RunExecutionEvent[];
}

export interface RunComparisonContextResponse {
  run: Run;
  peerRuns: Run[];
  architectureDistribution: DashboardDistributionItem[];
  scenarioDistribution: DashboardDistributionItem[];
}

export interface ReviewTask {
  id: string;
  conversationId: string;
  messageId: string;
  reason: string;
  status: ReviewTaskStatus;
  createdAt: string;
  resolvedAt?: string | null;
  metadata: JsonObject;
}

export interface DashboardTotals {
  conversations: number;
  runs: number;
  runsCompleted: number;
  runsFailed: number;
  runsHumanReview: number;
  messages: number;
  attachments: number;
  events: number;
  averageRunDurationMs?: number | null;
}

export interface DashboardDistributionItem {
  key: string;
  count: number;
  averageRunDurationMs?: number | null;
}

export interface DashboardConversationItem {
  conversationId: string;
  status: ConversationStatus;
  updatedAt: string;
  latestRunId?: string | null;
  lastMessage?: string | null;
  runCount: number;
  reviewPending: boolean;
}

export interface DashboardMetricsResponse {
  generatedAt: string;
  totals: DashboardTotals;
  byArchitecture: DashboardDistributionItem[];
  byModel: DashboardDistributionItem[];
  byScenario: DashboardDistributionItem[];
  byAttachmentType: DashboardDistributionItem[];
  byTool?: DashboardDistributionItem[];
  latencyPercentiles?: JsonObject;
  conversations: DashboardConversationItem[];
}

export interface ConversationSummary {
  conversationId: string;
  status: ConversationStatus;
  channel: ChannelType;
  architectureMode?: string | null;
  updatedAt: string;
  lastMessage?: string | null;
  messageCount: number;
  eventCount: number;
  latestRunId?: string | null;
  reviewPending: boolean;
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
  runId?: string | null;
}

export interface ConversationDetailResponse {
  conversation: Conversation;
  messages: Message[];
  attachments: Attachment[];
  runs: Run[];
  events: ProcessingEvent[];
  reviewTasks: ReviewTask[];
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
}

export interface ReviewTaskListResponse {
  reviewTasks: ReviewTask[];
}

export interface ResolveReviewTaskRequest {
  status: Extract<ReviewTaskStatus, "resolved" | "cancelled" | "in_review">;
  note?: string;
  resolvedBy?: string;
}

export interface MessageListResponse {
  conversationId: string;
  messages: Message[];
  attachments: Attachment[];
}
