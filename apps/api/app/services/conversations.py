from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.db.mappers import conversation_to_schema
from app.db.models import ConversationModel
from app.schemas.api import CreateConversationRequest
from app.schemas.domain import Conversation
from app.schemas.enums import ConversationStatus


class ConversationService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_conversation(self, request: CreateConversationRequest) -> Conversation:
        now = datetime.now(UTC)
        metadata_json = request.metadata.model_dump(
            by_alias=True,
            mode="json",
            exclude_none=True,
        )
        conversation = ConversationModel(
            id=uuid4(),
            channel=request.channel.value,
            created_at=now,
            updated_at=now,
            status=ConversationStatus.ACTIVE.value,
            user_session_id=request.user_session_id,
            metadata_json=metadata_json,
        )
        self._db.add(conversation)
        self._db.commit()
        self._db.refresh(conversation)
        return conversation_to_schema(conversation)

    def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        conversation = self._db.get(ConversationModel, conversation_id)
        if conversation is None:
            return None
        return conversation_to_schema(conversation)
