from app.db.models import AttachmentModel, ConversationModel, MessageModel, ProcessingEventModel
from app.schemas.domain import (
    Attachment,
    Conversation,
    Message,
    ModelContext,
    OperationalMetadata,
    ProcessingEvent,
)
from app.schemas.enums import (
    AttachmentStatus,
    ChannelType,
    ConversationStatus,
    MessageDirection,
    MessageStatus,
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
