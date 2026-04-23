from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.mappers import run_to_schema
from app.db.models import ConversationModel, MessageModel, RunModel
from app.schemas.domain import Run, RunExperimentMetadata
from app.schemas.enums import RunStatus


class RunValidationError(ValueError):
    pass


class RunService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_run(
        self,
        *,
        conversation_id: UUID,
        message_id: UUID,
        correlation_id: UUID,
        experiment: RunExperimentMetadata,
        ai_session_id: str | None = None,
        trace_id: str | None = None,
        status: RunStatus = RunStatus.PENDING,
    ) -> Run:
        conversation = self._db.get(ConversationModel, conversation_id)
        if conversation is None:
            raise RunValidationError("Conversation not found")
        message = self._db.get(MessageModel, message_id)
        if message is None or message.conversation_id != conversation_id:
            raise RunValidationError("Message not found for conversation")

        now = datetime.now(UTC)
        model = RunModel(
            id=uuid4(),
            conversation_id=conversation_id,
            message_id=message_id,
            correlation_id=correlation_id,
            ai_session_id=ai_session_id,
            trace_id=trace_id,
            status=status.value,
            started_at=now if status == RunStatus.RUNNING else None,
            experiment_json=experiment.model_dump(
                by_alias=True,
                mode="json",
                exclude_none=True,
            ),
            summary_json={},
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return run_to_schema(model)

    def list_conversation_runs(self, conversation_id: UUID) -> list[Run]:
        statement = (
            select(RunModel)
            .where(RunModel.conversation_id == conversation_id)
            .order_by(RunModel.created_at, RunModel.id)
        )
        return [run_to_schema(model) for model in self._db.scalars(statement).all()]
