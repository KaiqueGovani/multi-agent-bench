from app.db.models import (
    AttachmentModel,
    ConversationModel,
    MessageModel,
    ProcessingEventModel,
    ReviewTaskModel,
    RunExecutionEventModel,
    RunExecutionProjectionModel,
    RunModel,
)
from app.schemas.domain import (
    Attachment,
    Conversation,
    Message,
    ModelContext,
    OperationalMetadata,
    ProcessingEvent,
    ReviewTask,
    Run,
    RunExecutionDetail,
    RunExecutionEvent,
    RunExecutionProjection,
    RunExperimentMetadata,
    RunSummary,
)
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


def conversation_to_schema(model: ConversationModel) -> Conversation:
    return Conversation(
        id=model.id,
        channel=ChannelType(model.channel),
        created_at=model.created_at,
        updated_at=model.updated_at,
        status=ConversationStatus(model.status),
        user_session_id=model.user_session_id,
        metadata=OperationalMetadata.model_validate(model.metadata_json or {}),
    )


def processing_event_to_schema(model: ProcessingEventModel) -> ProcessingEvent:
    return ProcessingEvent(
        id=model.id,
        conversation_id=model.conversation_id,
        message_id=model.message_id,
        event_type=ProcessingEventType(model.event_type),
        actor_name=model.actor_name,
        parent_event_id=model.parent_event_id,
        correlation_id=model.correlation_id,
        payload=model.payload_json or {},
        created_at=model.created_at,
        duration_ms=model.duration_ms,
        status=ProcessingStatus(model.status),
    )


def message_to_schema(model: MessageModel) -> Message:
    return Message(
        id=model.id,
        conversation_id=model.conversation_id,
        direction=MessageDirection(model.direction),
        content_text=model.content_text,
        created_at_client=model.created_at_client,
        created_at_server=model.created_at_server,
        status=MessageStatus(model.status),
        correlation_id=model.correlation_id,
        metadata=OperationalMetadata.model_validate(model.metadata_json or {}),
        model_context=(
            ModelContext.model_validate(model.model_context_json)
            if model.model_context_json
            else None
        ),
    )


def attachment_to_schema(model: AttachmentModel) -> Attachment:
    return Attachment(
        id=model.id,
        message_id=model.message_id,
        storage_key=model.storage_key,
        original_filename=model.original_filename,
        mime_type=model.mime_type,
        size_bytes=model.size_bytes,
        checksum=model.checksum,
        width=model.width,
        height=model.height,
        created_at=model.created_at,
        status=AttachmentStatus(model.status),
        metadata=OperationalMetadata.model_validate(model.metadata_json or {}),
    )


def review_task_to_schema(model: ReviewTaskModel) -> ReviewTask:
    return ReviewTask(
        id=model.id,
        conversation_id=model.conversation_id,
        message_id=model.message_id,
        reason=model.reason,
        status=ReviewTaskStatus(model.status),
        created_at=model.created_at,
        resolved_at=model.resolved_at,
        metadata=OperationalMetadata.model_validate(model.metadata_json or {}),
    )


def run_to_schema(model: RunModel) -> Run:
    return Run(
        id=model.id,
        conversation_id=model.conversation_id,
        message_id=model.message_id,
        correlation_id=model.correlation_id,
        external_run_id=model.external_run_id,
        ai_session_id=model.ai_session_id,
        trace_id=model.trace_id,
        status=RunStatus(model.status),
        started_at=model.started_at,
        finished_at=model.finished_at,
        total_duration_ms=model.total_duration_ms,
        human_review_required=model.human_review_required,
        final_outcome=model.final_outcome,
        experiment=RunExperimentMetadata.model_validate(model.experiment_json or {}),
        summary=RunSummary.model_validate(model.summary_json or {}),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def run_execution_event_to_schema(model: RunExecutionEventModel) -> RunExecutionEvent:
    return RunExecutionEvent(
        id=model.id,
        run_id=model.run_id,
        conversation_id=model.conversation_id,
        message_id=model.message_id,
        correlation_id=model.correlation_id,
        event_family=model.event_family,
        event_name=model.event_name,
        sequence_no=model.sequence_no,
        created_at=model.created_at,
        status=ProcessingStatus(model.status),
        actor_name=model.actor_name,
        node_id=model.node_id,
        tool_name=model.tool_name,
        source=model.source,
        external_event_id=model.external_event_id,
        duration_ms=model.duration_ms,
        payload=model.payload_json or {},
    )


def run_execution_projection_to_schema(
    model: RunExecutionProjectionModel,
) -> RunExecutionProjection:
    return RunExecutionProjection(
        run_id=model.run_id,
        conversation_id=model.conversation_id,
        message_id=model.message_id,
        architecture_mode=model.architecture_mode,
        run_status=RunStatus(model.run_status),
        active_node_id=model.active_node_id,
        active_actor_name=model.active_actor_name,
        current_phase=model.current_phase,
        source=model.source,
        architecture_view=model.architecture_view_json or {},
        metrics=model.metrics_json or {},
        state=model.state_json or {},
        updated_at=model.updated_at,
    )
