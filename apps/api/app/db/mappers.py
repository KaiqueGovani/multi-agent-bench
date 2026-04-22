from app.db.models import ConversationModel
from app.schemas.domain import Conversation, OperationalMetadata
from app.schemas.enums import ChannelType, ConversationStatus


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

