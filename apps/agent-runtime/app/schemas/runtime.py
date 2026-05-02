from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda field_name: "".join(
            word.capitalize() if index else word
            for index, word in enumerate(field_name.split("_"))
        ),
        populate_by_name=True,
    )


JsonObject = dict[str, Any]


class OperationalMetadata(ApiModel):
    model_config = ConfigDict(
        alias_generator=lambda field_name: "".join(
            word.capitalize() if index else word
            for index, word in enumerate(field_name.split("_"))
        ),
        populate_by_name=True,
        extra="allow",
    )

    architecture_mode: str | None = None
    runtime_mode: str | None = None
    review_required: bool | None = None


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
    direction: str
    content_text: str | None = None
    created_at_server: datetime
    status: str
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
    latest_message: RuntimeMessageSnapshot
    conversation_history: list[RuntimeMessageSnapshot] = Field(default_factory=list)
    callback: RuntimeCallbackConfig


class RuntimeDispatchResponse(ApiModel):
    accepted: bool = True
    run_id: UUID
    status: Literal["accepted"] = "accepted"


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
    handoff_count: int | None = None
    stop_reason: str | None = None
    estimated_cost: float | None = None
    final_outcome: str | None = None


class CompleteRunRequest(ApiModel):
    status: str
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
    status: str
    actor_name: str | None = None
    node_id: str | None = None
    tool_name: str | None = None
    source: str | None = None
    duration_ms: int | None = None
    external_event_id: str | None = None
    payload: JsonObject = Field(default_factory=dict)


class HealthResponse(ApiModel):
    status: str
    service: str
    version: str
    environment: str
