from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.adapters.storage import LocalStorageAdapter, S3CompatibleStorageAdapter
from app.db.mappers import conversation_to_schema, review_task_to_schema
from app.db.models import (
    ConversationModel,
    AttachmentModel,
    MessageModel,
    ProcessingEventModel,
    ReviewTaskModel,
    RunModel,
    RunExecutionEventModel,
    RunExecutionProjectionModel,
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

    def delete_conversation(self, conversation_id: UUID) -> bool:
        # Serialize against title/message creation. Bulk deletes leave cascading
        # foreign keys in charge rather than ORM relationships setting IDs null.
        conversation = self._db.scalar(select(ConversationModel).where(
            ConversationModel.id == conversation_id).with_for_update())
        if conversation is None:
            return False
        message_ids = select(MessageModel.id).where(MessageModel.conversation_id == conversation_id)
        attachments = self._db.scalars(select(AttachmentModel).where(
            AttachmentModel.message_id.in_(message_ids))).all()
        deletions = []
        for attachment in attachments:
            expected = f"attachments/{conversation_id}/{attachment.message_id}/{attachment.id}-"
            if not attachment.storage_key.startswith(expected):
                raise ValueError("Attachment storage key does not belong to this conversation")
            metadata = attachment.metadata_json or {}
            provider = metadata.get("storageProvider") or self._settings.storage_provider
            if provider == "local":
                adapter = LocalStorageAdapter()
                adapter.resolve(attachment.storage_key, reject_symlinks=True)  # Validate every path first.
            elif provider in {"s3", "minio"}:
                adapter = S3CompatibleStorageAdapter(bucket=metadata.get("storageBucket"))
                if ".." in attachment.storage_key.split("/"):
                    raise ValueError("Invalid attachment storage key")
            else:
                raise ValueError("Unknown attachment storage provider")
            deletions.append((adapter, attachment.storage_key))

        # Missing objects are harmless on retry. On storage failure no database
        # rows are committed, preserving the keys needed to retry cleanup.
        for adapter, key in deletions:
            adapter.delete(key)
        for model in (RunExecutionEventModel, RunExecutionProjectionModel, ReviewTaskModel,
                      ProcessingEventModel, RunModel):
            self._db.execute(delete(model).where(model.conversation_id == conversation_id),
                             execution_options={"synchronize_session": False})
        self._db.execute(delete(AttachmentModel).where(AttachmentModel.message_id.in_(message_ids)),
                         execution_options={"synchronize_session": False})
        self._db.execute(delete(MessageModel).where(MessageModel.conversation_id == conversation_id),
                         execution_options={"synchronize_session": False})
        self._db.execute(delete(ConversationModel).where(ConversationModel.id == conversation_id),
                         execution_options={"synchronize_session": False})
        self._db.commit()
        return True

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
            title=(model.metadata_json or {}).get("title"),
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
