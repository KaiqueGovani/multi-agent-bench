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
    RunStatus,
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


class RunExperimentMetadata(ApiModel):
    model_config = ConfigDict(
        alias_generator=lambda field_name: "".join(
            word.capitalize() if index else word
            for index, word in enumerate(field_name.split("_"))
        ),
        populate_by_name=True,
        extra="allow",
    )

    architecture_family: str | None = None
    architecture_key: str
    architecture_version: str | None = None
    routing_strategy: str | None = None
    memory_strategy: str | None = None
    tool_executor_mode: str | None = None
    review_policy_version: str | None = None
    model_provider: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    prompt_bundle_version: str | None = None
    toolset_version: str | None = None
    experiment_id: str | None = None
    scenario_id: str | None = None
    runtime_commit_sha: str | None = None


class RunSummary(ApiModel):
    model_config = ConfigDict(
        alias_generator=lambda field_name: "".join(
            word.capitalize() if index else word
            for index, word in enumerate(field_name.split("_"))
        ),
        populate_by_name=True,
        extra="allow",
    )

    time_to_first_public_event_ms: int | None = None
    time_to_first_partial_response_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    tool_call_count: int | None = None
    tool_error_count: int | None = None
    loop_count: int | None = None
    stop_reason: str | None = None
    estimated_cost: float | None = None
    final_outcome: str | None = None


class Run(ApiModel):
    id: UUID
    conversation_id: UUID
    message_id: UUID
    correlation_id: UUID
    external_run_id: str | None = None
    ai_session_id: str | None = None
    trace_id: str | None = None
    status: RunStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    total_duration_ms: int | None = None
    human_review_required: bool | None = None
    final_outcome: str | None = None
    experiment: RunExperimentMetadata
    summary: RunSummary = Field(default_factory=RunSummary)
    created_at: datetime
    updated_at: datetime


class RuntimeAttachmentDescriptor(ApiModel):
    attachment_id: UUID
    message_id: UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    checksum: str
    width: int | None = None
    height: int | None = None
    page_count: int | None = None
    retrieval_url: str
    metadata: OperationalMetadata = Field(default_factory=OperationalMetadata)


class RuntimeMessageSnapshot(ApiModel):
    id: UUID
    direction: MessageDirection
    content_text: str | None = None
    created_at_server: datetime
    status: MessageStatus
    correlation_id: UUID
    metadata: OperationalMetadata = Field(default_factory=OperationalMetadata)
    attachments: list[RuntimeAttachmentDescriptor] = Field(default_factory=list)


class RuntimeCallbackConfig(ApiModel):
    base_url: str
    api_key: str | None = None
    ai_service_secret: str | None = None


class RuntimeDispatchRequest(ApiModel):
    run_id: UUID
    conversation_id: UUID
    message_id: UUID
    correlation_id: UUID
    ai_session_id: str | None = None
    traceparent: str | None = None
    baggage: str | None = None
    architecture_mode: str
    experiment: RunExperimentMetadata
    latest_message: "RuntimeMessageSnapshot"
    conversation_history: list["RuntimeMessageSnapshot"] = Field(default_factory=list)
    callback: RuntimeCallbackConfig


class RunExecutionEvent(ApiModel):
    id: UUID
    run_id: UUID
    conversation_id: UUID
    message_id: UUID
    correlation_id: UUID
    event_family: str
    event_name: str
    sequence_no: int
    created_at: datetime
    status: ProcessingStatus
    actor_name: str | None = None
    node_id: str | None = None
    tool_name: str | None = None
    source: str | None = None
    external_event_id: str | None = None
    duration_ms: int | None = None
    payload: JsonObject = Field(default_factory=dict)


class RunExecutionProjection(ApiModel):
    run_id: UUID
    conversation_id: UUID
    message_id: UUID
    architecture_mode: str
    run_status: RunStatus
    active_node_id: str | None = None
    active_actor_name: str | None = None
    current_phase: str | None = None
    source: str | None = None
    architecture_view: JsonObject = Field(default_factory=dict)
    metrics: JsonObject = Field(default_factory=dict)
    state: JsonObject = Field(default_factory=dict)
    updated_at: datetime


class RunExecutionDetail(ApiModel):
    run: Run
    projection: RunExecutionProjection | None = None
    execution_events: list[RunExecutionEvent] = Field(default_factory=list)


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


RuntimeDispatchRequest.model_rebuild()
