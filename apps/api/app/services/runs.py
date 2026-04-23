from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.mappers import run_to_schema
from app.db.models import ConversationModel, MessageModel, RunModel
from app.schemas.domain import Run, RunExperimentMetadata, RunSummary
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

    def mark_running(self, run_id: UUID) -> Run | None:
        model = self._db.get(RunModel, run_id)
        if model is None:
            return None
        model.status = RunStatus.RUNNING.value
        if model.started_at is None:
            model.started_at = datetime.now(UTC)
        self._db.commit()
        self._db.refresh(model)
        return run_to_schema(model)

    def complete_run(
        self,
        run_id: UUID,
        *,
        status: RunStatus = RunStatus.COMPLETED,
        external_run_id: str | None = None,
        trace_id: str | None = None,
        total_duration_ms: int | None = None,
        human_review_required: bool | None = None,
        final_outcome: str | None = None,
        summary: RunSummary | None = None,
    ) -> Run | None:
        model = self._db.get(RunModel, run_id)
        if model is None:
            return None
        model.status = status.value
        model.external_run_id = external_run_id or model.external_run_id
        model.trace_id = trace_id or model.trace_id
        model.finished_at = datetime.now(UTC)
        model.total_duration_ms = total_duration_ms
        model.human_review_required = human_review_required
        model.final_outcome = final_outcome
        if summary is not None:
            model.summary_json = summary.model_dump(
                by_alias=True,
                mode="json",
                exclude_none=True,
            )
        self._db.commit()
        self._db.refresh(model)
        return run_to_schema(model)

    def fail_run(self, run_id: UUID, *, reason: str) -> Run | None:
        return self.complete_run(
            run_id,
            status=RunStatus.FAILED,
            final_outcome="dispatch_failed",
            summary=RunSummary(stop_reason=reason, final_outcome="dispatch_failed"),
        )
