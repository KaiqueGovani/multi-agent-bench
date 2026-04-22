from datetime import UTC, datetime
from threading import Lock
from uuid import UUID, uuid4

from app.schemas.api import CreateConversationRequest
from app.schemas.domain import Conversation
from app.schemas.enums import ConversationStatus


class ConversationService:
    def __init__(self) -> None:
        self._conversations: dict[UUID, Conversation] = {}
        self._lock = Lock()

    def create_conversation(self, request: CreateConversationRequest) -> Conversation:
        now = datetime.now(UTC)
        conversation = Conversation(
            id=uuid4(),
            channel=request.channel,
            created_at=now,
            updated_at=now,
            status=ConversationStatus.ACTIVE,
            user_session_id=request.user_session_id,
            metadata=request.metadata,
        )
        with self._lock:
            self._conversations[conversation.id] = conversation
        return conversation

    def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        with self._lock:
            return self._conversations.get(conversation_id)


_conversation_service = ConversationService()


def get_conversation_service() -> ConversationService:
    return _conversation_service

