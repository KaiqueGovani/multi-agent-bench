from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.mappers import conversation_to_schema, review_task_to_schema
from app.db.models import (
    ConversationModel,
    MessageModel,
    ProcessingEventModel,
    ReviewTaskModel,
    RunModel,
)
from app.schemas.api import ConversationSummary, CreateConversationRequest
from app.schemas.domain import Conversation, ReviewTask
from app.schemas.enums import (
    ConversationStatus,
    ProcessingEventType,
    ProcessingStatus,
    ReviewTaskStatus,
)
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

    def list_conversation_summaries(self, *, limit: int = 30) -> list[ConversationSummary]:
        statement = (
            select(ConversationModel)
            .order_by(ConversationModel.updated_at.desc(), ConversationModel.created_at.desc())
            .limit(limit)
        )
        return [
            self._conversation_summary(model)
            for model in self._db.scalars(statement).all()
        ]

    def list_review_tasks(self, conversation_id: UUID) -> list[ReviewTask]:
        statement = (
            select(ReviewTaskModel)
            .where(ReviewTaskModel.conversation_id == conversation_id)
            .order_by(ReviewTaskModel.created_at, ReviewTaskModel.id)
        )
        return [review_task_to_schema(task) for task in self._db.scalars(statement).all()]

    def _conversation_summary(self, model: ConversationModel) -> ConversationSummary:
        last_message = self._db.scalars(
            select(MessageModel)
            .where(MessageModel.conversation_id == model.id)
            .order_by(MessageModel.created_at_server.desc(), MessageModel.id.desc())
            .limit(1)
        ).first()
        latest_run = self._db.scalars(
            select(RunModel)
            .where(RunModel.conversation_id == model.id)
            .order_by(RunModel.created_at.desc(), RunModel.id.desc())
            .limit(1)
        ).first()
        message_count = self._count_for(MessageModel, model.id)
        event_count = self._count_for(ProcessingEventModel, model.id)
        pending_reviews = self._db.scalar(
            select(func.count())
            .select_from(ReviewTaskModel)
            .where(
                ReviewTaskModel.conversation_id == model.id,
                ReviewTaskModel.status.in_(
                    [ReviewTaskStatus.OPEN.value, ReviewTaskStatus.IN_REVIEW.value]
                ),
            )
        )

        return ConversationSummary(
            conversation_id=model.id,
            status=ConversationStatus(model.status),
            channel=model.channel,
            architecture_mode=(model.metadata_json or {}).get("architectureMode"),
            updated_at=model.updated_at,
            last_message=last_message.content_text if last_message else None,
            message_count=message_count,
            event_count=event_count,
            latest_run_id=latest_run.id if latest_run else None,
            review_pending=bool(pending_reviews),
        )

    def _count_for(self, model: type[MessageModel] | type[ProcessingEventModel], conversation_id: UUID) -> int:
        return int(
            self._db.scalar(
                select(func.count())
                .select_from(model)
                .where(model.conversation_id == conversation_id)
            )
            or 0
        )
