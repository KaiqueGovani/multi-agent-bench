from enum import StrEnum


class ChannelType(StrEnum):
    WEB_CHAT = "web_chat"
    WHATSAPP = "whatsapp"


class ConversationStatus(StrEnum):
    ACTIVE = "active"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class MessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    SYSTEM = "system"


class MessageStatus(StrEnum):
    DRAFT = "draft"
    RECEIVED = "received"
    ACCEPTED = "accepted"
    VALIDATING = "validating"
    PROCESSING = "processing"
    FORWARDED = "forwarded"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class AttachmentStatus(StrEnum):
    RECEIVED = "received"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    VALIDATED = "validated"
    REJECTED = "rejected"
    ERROR = "error"


class ProcessingEventType(StrEnum):
    CONVERSATION_CREATED = "conversation.created"
    MESSAGE_RECEIVED = "message.received"
    ATTACHMENT_UPLOAD_STARTED = "attachment.upload.started"
    ATTACHMENT_UPLOAD_COMPLETED = "attachment.upload.completed"
    ATTACHMENT_VALIDATION_STARTED = "attachment.validation.started"
    ATTACHMENT_VALIDATION_COMPLETED = "attachment.validation.completed"
    PROCESSING_STARTED = "processing.started"
    ACTOR_INVOKED = "actor.invoked"
    ACTOR_PROGRESS = "actor.progress"
    ACTOR_COMPLETED = "actor.completed"
    ACTOR_FAILED = "actor.failed"
    HANDOFF_REQUESTED = "handoff.requested"
    REVIEW_REQUIRED = "review.required"
    RESPONSE_PARTIAL = "response.partial"
    RESPONSE_FINAL = "response.final"
    PROCESSING_COMPLETED = "processing.completed"


class ProcessingStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class ReviewTaskStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class ArchitectureMode(StrEnum):
    CENTRALIZED_ORCHESTRATION = "centralized_orchestration"
    STRUCTURED_WORKFLOW = "structured_workflow"
    DECENTRALIZED_SWARM = "decentralized_swarm"


class RuntimeMode(StrEnum):
    MOCK = "mock"
    REAL = "real"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
