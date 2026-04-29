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
    RunExecutionDetail,
    RunExecutionEvent,
    RunExecutionProjection,
    RuntimeDispatchRequest,
    RunSummary,
)
from app.schemas.enums import (
    ChannelType,
    ConversationStatus,
    MessageStatus,
    ProcessingEventType,
    ProcessingStatus,
    ReviewTaskStatus,
    RunStatus,
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


class ConversationSummary(ApiModel):
    conversation_id: UUID
    status: ConversationStatus
    channel: ChannelType
    architecture_mode: str | None = None
    updated_at: datetime
    last_message: str | None = None
    message_count: int
    event_count: int
    latest_run_id: UUID | None = None
    review_pending: bool


class ConversationListResponse(ApiModel):
    conversations: list[ConversationSummary] = Field(default_factory=list)


class DashboardTotals(ApiModel):
    conversations: int = 0
    runs: int = 0
    runs_completed: int = 0
    runs_failed: int = 0
    runs_human_review: int = 0
    messages: int = 0
    attachments: int = 0
    events: int = 0
    average_run_duration_ms: int | None = None


class DashboardDistributionItem(ApiModel):
    key: str
    count: int
    average_run_duration_ms: int | None = None


class DashboardConversationItem(ApiModel):
    conversation_id: UUID
    status: ConversationStatus
    updated_at: datetime
    latest_run_id: UUID | None = None
    last_message: str | None = None
    run_count: int
    review_pending: bool


class DashboardMetricsResponse(ApiModel):
    generated_at: datetime
    totals: DashboardTotals = Field(default_factory=DashboardTotals)
    by_architecture: list[DashboardDistributionItem] = Field(default_factory=list)
    by_model: list[DashboardDistributionItem] = Field(default_factory=list)
    by_scenario: list[DashboardDistributionItem] = Field(default_factory=list)
    by_attachment_type: list[DashboardDistributionItem] = Field(default_factory=list)
    by_tool: list[DashboardDistributionItem] = Field(default_factory=list)
    latency_percentiles: JsonObject = Field(default_factory=dict)
    conversations: list[DashboardConversationItem] = Field(default_factory=list)


class ReviewTaskListResponse(ApiModel):
    review_tasks: list[ReviewTask] = Field(default_factory=list)


class ResolveReviewTaskRequest(ApiModel):
    status: ReviewTaskStatus = ReviewTaskStatus.RESOLVED
    note: str | None = None
    resolved_by: str | None = None


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
    run_id: UUID | None = None


class CompleteRunRequest(ApiModel):
    status: RunStatus = RunStatus.COMPLETED
    external_run_id: str | None = None
    trace_id: str | None = None
    finished_at: datetime | None = None
    total_duration_ms: int | None = None
    human_review_required: bool | None = None
    final_outcome: str | None = None
    summary: RunSummary = Field(default_factory=RunSummary)


class IngestRunExecutionEventRequest(ApiModel):
    run_id: UUID
    conversation_id: UUID
    message_id: UUID
    correlation_id: UUID
    event_family: str
    event_name: str
    status: ProcessingStatus
    actor_name: str | None = None
    node_id: str | None = None
    tool_name: str | None = None
    source: str | None = None
    duration_ms: int | None = None
    external_event_id: str | None = None
    payload: JsonObject = Field(default_factory=dict)


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
    run_id: UUID | None = None
    event_type: ProcessingEventType
    actor_name: str | None = None
    parent_event_id: UUID | None = None
    correlation_id: UUID
    payload: JsonObject = Field(default_factory=dict)
    duration_ms: int | None = None
    status: ProcessingStatus
    external_event_id: str | None = None
    source: str = "ai_service"


class RunExecutionResponse(ApiModel):
    run: Run
    projection: RunExecutionProjection | None = None
    execution_events: list[RunExecutionEvent] = Field(default_factory=list)


class RunComparisonContextResponse(ApiModel):
    run: Run
    peer_runs: list[Run] = Field(default_factory=list)
    architecture_distribution: list[DashboardDistributionItem] = Field(default_factory=list)
    scenario_distribution: list[DashboardDistributionItem] = Field(default_factory=list)


class RuntimeDispatchResponse(ApiModel):
    accepted: bool = True
    run_id: UUID
    status: str = "accepted"


class RuntimeDispatchEnvelope(ApiModel):
    dispatched_at: datetime
    request: RuntimeDispatchRequest
