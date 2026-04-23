from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.domain import (
    ApiModel,
    Attachment,
    Conversation,
    JsonObject,
    Message,
    OperationalMetadata,
    ProcessingEvent,
    ReviewTask,
    Run,
)
from app.schemas.enums import (
    ChannelType,
    ConversationStatus,
    MessageStatus,
    ProcessingEventType,
    ProcessingStatus,
)


class HealthResponse(ApiModel):
    status: str
    service: str
    version: str
    environment: str


class CreateConversationRequest(ApiModel):
    channel: ChannelType = ChannelType.WEB_CHAT
    user_session_id: str | None = None
    metadata: OperationalMetadata = Field(default_factory=OperationalMetadata)


class CreateConversationResponse(ApiModel):
    conversation_id: UUID
    status: ConversationStatus
    channel: ChannelType
    created_at: datetime


class ConversationDetailResponse(ApiModel):
    conversation: Conversation
    messages: list[Message] = Field(default_factory=list)
    attachments: list[Attachment] = Field(default_factory=list)
    runs: list[Run] = Field(default_factory=list)
    events: list[ProcessingEvent] = Field(default_factory=list)
    review_tasks: list[ReviewTask] = Field(default_factory=list)


class MessageListResponse(ApiModel):
    conversation_id: UUID
    messages: list[Message] = Field(default_factory=list)
    attachments: list[Attachment] = Field(default_factory=list)


class SendMessageResponse(ApiModel):
    message_id: UUID
    conversation_id: UUID
    status: MessageStatus
    correlation_id: UUID
    accepted_at: datetime


class SseProcessingEvent(ApiModel):
    event_id: UUID
    event_type: ProcessingEventType
    actor_name: str | None = None
    message_id: UUID | None = None
    conversation_id: UUID
    correlation_id: UUID
    status: ProcessingStatus
    created_at: datetime
    duration_ms: int | None = None
    payload: JsonObject = Field(default_factory=dict)


class IngestProcessingEventRequest(ApiModel):
    conversation_id: UUID
    message_id: UUID | None = None
    event_type: ProcessingEventType
    actor_name: str | None = None
    parent_event_id: UUID | None = None
    correlation_id: UUID
    payload: JsonObject = Field(default_factory=dict)
    duration_ms: int | None = None
    status: ProcessingStatus
    external_event_id: str | None = None
    source: str = "ai_service"
