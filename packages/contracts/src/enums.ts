export const CHANNEL_TYPES = [
  "web_chat",
  "whatsapp",
] as const;

export type ChannelType = (typeof CHANNEL_TYPES)[number];

export const CONVERSATION_STATUSES = [
  "active",
  "waiting",
  "completed",
  "error",
  "human_review_required",
] as const;

export type ConversationStatus = (typeof CONVERSATION_STATUSES)[number];

export const MESSAGE_DIRECTIONS = [
  "inbound",
  "outbound",
  "system",
] as const;

export type MessageDirection = (typeof MESSAGE_DIRECTIONS)[number];

export const MESSAGE_STATUSES = [
  "draft",
  "received",
  "accepted",
  "validating",
  "processing",
  "forwarded",
  "waiting",
  "completed",
  "error",
  "human_review_required",
] as const;

export type MessageStatus = (typeof MESSAGE_STATUSES)[number];

export const ATTACHMENT_STATUSES = [
  "received",
  "uploading",
  "uploaded",
  "validating",
  "validated",
  "rejected",
  "error",
] as const;

export type AttachmentStatus = (typeof ATTACHMENT_STATUSES)[number];

export const PROCESSING_EVENT_TYPES = [
  "conversation.created",
  "message.received",
  "attachment.upload.started",
  "attachment.upload.completed",
  "attachment.validation.started",
  "attachment.validation.completed",
  "processing.started",
  "actor.invoked",
  "actor.progress",
  "actor.completed",
  "actor.failed",
  "handoff.requested",
  "review.required",
  "response.partial",
  "response.final",
  "processing.completed",
] as const;

export type ProcessingEventType = (typeof PROCESSING_EVENT_TYPES)[number];

export const PROCESSING_STATUSES = [
  "pending",
  "running",
  "completed",
  "failed",
  "waiting",
  "human_review_required",
] as const;

export type ProcessingStatus = (typeof PROCESSING_STATUSES)[number];

export const REVIEW_TASK_STATUSES = [
  "open",
  "in_review",
  "resolved",
  "cancelled",
] as const;

export type ReviewTaskStatus = (typeof REVIEW_TASK_STATUSES)[number];

export const ARCHITECTURE_MODES = [
  "centralized_orchestration",
  "structured_workflow",
  "decentralized_swarm",
] as const;

export type ArchitectureMode = (typeof ARCHITECTURE_MODES)[number];

export const RUNTIME_MODES = [
  "mock",
  "real",
] as const;

export type RuntimeMode = (typeof RUNTIME_MODES)[number];

export const MOCK_ACTOR_NAMES = [
  "router_agent",
  "faq_agent",
  "stock_agent",
  "image_intake_agent",
  "supervisor_agent",
] as const;

export type MockActorName = (typeof MOCK_ACTOR_NAMES)[number];

