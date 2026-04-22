from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import (
    AttachmentStatus,
    ChannelType,
    ConversationStatus,
    MessageDirection,
    MessageStatus,
    ProcessingEventType,
    ProcessingStatus,
    ReviewTaskStatus,
)

JsonObject = dict[str, Any]


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda field_name: "".join(
            word.capitalize() if index else word
            for index, word in enumerate(field_name.split("_"))
        ),
        populate_by_name=True,
    )


class ModelContext(ApiModel):
    language: str | None = None
    current_time: datetime | None = None
    conversation_summary: str | None = None
    attachment_types: list[str] = Field(default_factory=list)
    inferred_intent: str | None = None


class OperationalMetadata(ApiModel):
    model_config = ConfigDict(
        alias_generator=lambda field_name: "".join(
            word.capitalize() if index else word
            for index, word in enumerate(field_name.split("_"))
        ),
        populate_by_name=True,
        extra="allow",
    )

    request_id: UUID | None = None
    correlation_id: UUID | None = None
    client_timestamp: datetime | None = None
    timezone: str | None = None
    locale: str | None = None
    user_agent: str | None = None
    device_type: str | None = None
    upload_duration_ms: int | None = None
    message_input_duration_ms: int | None = None
    file_count: int | None = None
    file_types: list[str] = Field(default_factory=list)
    file_sizes: list[int] = Field(default_factory=list)
    processing_start_at: datetime | None = None
    processing_end_at: datetime | None = None
    total_duration_ms: int | None = None
    step_duration_ms: int | None = None
    channel: ChannelType | None = None
    architecture_mode: str | None = None
    runtime_mode: str | None = None
    review_required: bool | None = None


class Conversation(ApiModel):
    id: UUID
    channel: ChannelType
    created_at: datetime
    updated_at: datetime
    status: ConversationStatus
    user_session_id: str | None = None
    metadata: OperationalMetadata = Field(default_factory=OperationalMetadata)


class Message(ApiModel):
    id: UUID
    conversation_id: UUID
    direction: MessageDirection
    content_text: str | None = None
    created_at_client: datetime | None = None
    created_at_server: datetime
    status: MessageStatus
    correlation_id: UUID
    metadata: OperationalMetadata = Field(default_factory=OperationalMetadata)
    model_context: ModelContext | None = None


class Attachment(ApiModel):
    id: UUID
    message_id: UUID
    storage_key: str
    original_filename: str
    mime_type: str
    size_bytes: int
    checksum: str
    width: int | None = None
    height: int | None = None
    created_at: datetime
    status: AttachmentStatus
    metadata: OperationalMetadata = Field(default_factory=OperationalMetadata)


class ProcessingEvent(ApiModel):
    id: UUID
    conversation_id: UUID
    message_id: UUID | None = None
    event_type: ProcessingEventType
    actor_name: str | None = None
    parent_event_id: UUID | None = None
    correlation_id: UUID
    payload: JsonObject = Field(default_factory=dict)
    created_at: datetime
    duration_ms: int | None = None
    status: ProcessingStatus


class ReviewTask(ApiModel):
    id: UUID
    conversation_id: UUID
    message_id: UUID
    reason: str
    status: ReviewTaskStatus
    created_at: datetime
    resolved_at: datetime | None = None
    metadata: OperationalMetadata = Field(default_factory=OperationalMetadata)


class NormalizedAttachmentInput(ApiModel):
    client_attachment_id: str | None = None
    original_filename: str
    mime_type: str
    size_bytes: int
    checksum: str | None = None
    width: int | None = None
    height: int | None = None
    metadata: OperationalMetadata = Field(default_factory=OperationalMetadata)


class NormalizedInboundMessage(ApiModel):
    channel: ChannelType
    conversation_id: UUID | None = None
    client_message_id: str | None = None
    user_session_id: str | None = None
    text: str | None = None
    attachments: list[NormalizedAttachmentInput] = Field(default_factory=list)
    created_at_client: datetime | None = None
    metadata: OperationalMetadata = Field(default_factory=OperationalMetadata)
    model_context: ModelContext | None = None


class NormalizedOutboundMessage(ApiModel):
    channel: ChannelType
    conversation_id: UUID
    message_id: UUID
    correlation_id: UUID
    text: str
    attachments: list[Attachment] = Field(default_factory=list)
    status: MessageStatus
    metadata: OperationalMetadata = Field(default_factory=OperationalMetadata)
    model_context: ModelContext | None = None
