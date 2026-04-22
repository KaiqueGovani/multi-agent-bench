from app.db.models import ConversationModel, ProcessingEventModel
from app.schemas.domain import Conversation, OperationalMetadata, ProcessingEvent
from app.schemas.enums import (
    ChannelType,
    ConversationStatus,
    ProcessingEventType,
    ProcessingStatus,
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
