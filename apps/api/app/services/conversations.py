from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.mappers import conversation_to_schema, review_task_to_schema
from app.db.models import ConversationModel, ReviewTaskModel
from app.schemas.api import CreateConversationRequest
from app.schemas.domain import Conversation, ReviewTask
from app.schemas.enums import ConversationStatus, ProcessingEventType, ProcessingStatus
from app.services.events import EventService


class ConversationService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._settings = get_settings()

    def create_conversation(self, request: CreateConversationRequest) -> Conversation:
        now = datetime.now(UTC)
        metadata = request.metadata.model_copy(
            update={
                "architecture_mode": (
                    request.metadata.architecture_mode
                    or self._settings.default_architecture_mode
                ),
                "channel": request.channel,
                "runtime_mode": request.metadata.runtime_mode or self._settings.runtime_mode,
            }
        )
        metadata_json = metadata.model_dump(
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
        self._db.flush()

        EventService(self._db).record_event(
            conversation_id=conversation.id,
            event_type=ProcessingEventType.CONVERSATION_CREATED,
            correlation_id=uuid4(),
            status=ProcessingStatus.COMPLETED,
            payload={
                "architectureMode": metadata.architecture_mode,
                "channel": request.channel.value,
                "requestId": str(metadata.request_id) if metadata.request_id else None,
                "runtimeMode": metadata.runtime_mode,
                "userSessionId": request.user_session_id,
            },
            commit=False,
            publish=False,
        )

        self._db.commit()
        self._db.refresh(conversation)
        return conversation_to_schema(conversation)

    def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        conversation = self._db.get(ConversationModel, conversation_id)
        if conversation is None:
            return None
        return conversation_to_schema(conversation)

    def list_review_tasks(self, conversation_id: UUID) -> list[ReviewTask]:
        statement = (
            select(ReviewTaskModel)
            .where(ReviewTaskModel.conversation_id == conversation_id)
            .order_by(ReviewTaskModel.created_at, ReviewTaskModel.id)
        )
        return [review_task_to_schema(task) for task in self._db.scalars(statement).all()]
