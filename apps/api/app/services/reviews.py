from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.mappers import review_task_to_schema
from app.db.models import ConversationModel, MessageModel, ReviewTaskModel, RunExecutionProjectionModel, RunModel
from app.schemas.domain import ReviewTask
from app.schemas.enums import (
    ConversationStatus,
    MessageStatus,
    ProcessingEventType,
    ProcessingStatus,
    ReviewTaskStatus,
    RunStatus,
)
from app.services.events import EventService
from app.services.event_bus import event_bus


class ReviewValidationError(ValueError):
    pass


class ReviewService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_open_review_tasks(self) -> list[ReviewTask]:
        statement = (
            select(ReviewTaskModel)
            .where(
                ReviewTaskModel.status.in_(
                    [ReviewTaskStatus.OPEN.value, ReviewTaskStatus.IN_REVIEW.value]
                )
            )
            .order_by(ReviewTaskModel.created_at, ReviewTaskModel.id)
        )
        return [review_task_to_schema(task) for task in self._db.scalars(statement).all()]

    def has_pending_reviews(self, conversation_id: UUID) -> bool:
        return self._db.scalar(select(ReviewTaskModel.id).where(
            ReviewTaskModel.conversation_id == conversation_id,
            ReviewTaskModel.status.in_([ReviewTaskStatus.OPEN.value, ReviewTaskStatus.IN_REVIEW.value]),
        ).limit(1)) is not None

    def ensure_run_review(
        self, run: RunModel, *, payload: dict | None = None, source: str = "ai_service"
    ) -> ReviewTaskModel | None:
        """Persist one handoff per inbound message in the caller's transaction.

        Lock the conversation shared by all callbacks. A completed adjudication
        is a durable decision: retries must neither reopen it nor create a task.
        Comparison runs remain historical measurements, not extra queue items.
        """
        if bool((run.experiment_json or {}).get("comparisonOnly")):
            return None
        conversation = self._db.scalar(select(ConversationModel).where(
            ConversationModel.id == run.conversation_id).with_for_update())
        message = self._db.get(MessageModel, run.message_id)
        if conversation is None or message is None or message.conversation_id != conversation.id:
            return None
        task = self._db.scalars(select(ReviewTaskModel).where(
            ReviewTaskModel.conversation_id == run.conversation_id,
            ReviewTaskModel.message_id == run.message_id,
        ).order_by(ReviewTaskModel.created_at.desc(), ReviewTaskModel.id.desc())).first()
        if task is not None and task.status not in {ReviewTaskStatus.OPEN.value, ReviewTaskStatus.IN_REVIEW.value}:
            message.status = MessageStatus.COMPLETED.value if task.status == ReviewTaskStatus.RESOLVED.value else MessageStatus.ERROR.value
            message.metadata_json = {**(message.metadata_json or {}), "reviewRequired": False,
                                     "reviewTaskId": str(task.id), "humanReviewResolution": task.status}
            return task
        payload = payload or {}
        if task is None:
            task = ReviewTaskModel(
                id=uuid4(), conversation_id=run.conversation_id, message_id=run.message_id,
                reason=str(payload.get("reason") or "Este atendimento requer avaliação de um profissional antes de ser concluído."),
                status=ReviewTaskStatus.OPEN.value,
                metadata_json={"runtimeRunId": str(run.id), "sourceMessageId": str(run.message_id), "source": source},
            )
            self._db.add(task)
            self._db.flush()
        elif not (task.metadata_json or {}).get("runtimeRunId"):
            task.metadata_json = {**(task.metadata_json or {}), "runtimeRunId": str(run.id),
                                  "sourceMessageId": str(run.message_id), "source": source}
        message.status = MessageStatus.HUMAN_REVIEW_REQUIRED.value
        message.metadata_json = {
            **(message.metadata_json or {}), "reviewRequired": True, "reviewTaskId": str(task.id),
        }
        conversation.status = ConversationStatus.HUMAN_REVIEW_REQUIRED.value
        conversation.updated_at = datetime.now(UTC)
        self._db.flush()
        return task

    def reconcile_missing_review_tasks(self, *, apply: bool = False) -> dict:
        """Recover only unresolved canonical runs already flagged for review."""
        candidates = self._db.scalars(select(RunModel).where(or_(
            RunModel.status == RunStatus.HUMAN_REVIEW_REQUIRED.value,
            RunModel.human_review_required.is_(True),
        )).order_by(RunModel.created_at, RunModel.id)).all()
        missing = []
        seen = set()
        for run in candidates:
            if bool((run.experiment_json or {}).get("comparisonOnly")) or run.message_id in seen:
                continue
            seen.add(run.message_id)
            existing = self._db.scalar(select(ReviewTaskModel.id).where(
                ReviewTaskModel.conversation_id == run.conversation_id,
                ReviewTaskModel.message_id == run.message_id,
            ).limit(1))
            if existing is not None or run.final_outcome in {"human_review_resolved", "human_review_cancelled"}:
                continue
            missing.append({"conversationId": str(run.conversation_id), "messageId": str(run.message_id), "runId": str(run.id)})
            if apply:
                self.ensure_run_review(run, source="review_reconciliation")
        if apply:
            self._db.commit()
        return {"applied": apply, "missingCount": len(missing), "reviews": missing}

    def resolve_review_task(
        self,
        review_task_id: UUID,
        *,
        status: ReviewTaskStatus,
        note: str | None = None,
        resolved_by: str | None = None,
    ) -> ReviewTask | None:
        task = self._db.get(ReviewTaskModel, review_task_id)
        if task is None:
            return None
        if status not in {
            ReviewTaskStatus.IN_REVIEW,
            ReviewTaskStatus.RESOLVED,
            ReviewTaskStatus.CANCELLED,
        }:
            raise ReviewValidationError("Review task can only be updated to in_review, resolved or cancelled")

        conversation = self._db.scalar(select(ConversationModel).where(
            ConversationModel.id == task.conversation_id).with_for_update())
        if conversation is None:
            return None
        self._db.refresh(task)
        if task.status in {ReviewTaskStatus.RESOLVED.value, ReviewTaskStatus.CANCELLED.value}:
            return review_task_to_schema(task)

        now = datetime.now(UTC)
        task.status = status.value
        task.resolved_at = now if status != ReviewTaskStatus.IN_REVIEW else None
        task.metadata_json = {
            **(task.metadata_json or {}),
            "humanNote": note,
            "resolvedBy": resolved_by,
            "resolutionStatus": status.value,
        }

        if status == ReviewTaskStatus.IN_REVIEW:
            self._db.flush()
            review_event = EventService(self._db).record_event(
                conversation_id=task.conversation_id,
                message_id=task.message_id,
                event_type=ProcessingEventType.ACTOR_PROGRESS,
                actor_name="human_reviewer",
                correlation_id=task.id,
                status=ProcessingStatus.WAITING,
                payload={
                    "source": "human_review",
                    "reviewTaskId": str(task.id),
                    "resolutionStatus": status.value,
                    "resolvedBy": resolved_by,
                    "note": note,
                },
                commit=False,
                publish=False,
            )
            self._db.commit()
            self._db.refresh(task)
            event_bus.publish(review_event)
            return review_task_to_schema(task)

        message = self._db.get(MessageModel, task.message_id)
        if message is not None:
            message.status = (
                MessageStatus.COMPLETED.value
                if status == ReviewTaskStatus.RESOLVED
                else MessageStatus.ERROR.value
            )
            message.metadata_json = {**(message.metadata_json or {}), "reviewRequired": False,
                                     "reviewTaskId": str(task.id), "humanReviewResolution": status.value}

        if conversation is not None and not self._has_open_reviews(task.conversation_id, exclude_id=task.id):
            active_runs = self._db.scalars(select(RunModel).where(
                RunModel.conversation_id == task.conversation_id,
                RunModel.message_id != task.message_id,
                RunModel.status.in_([RunStatus.PENDING.value, RunStatus.RUNNING.value]),
            ))
            active_work = any(not bool((run.experiment_json or {}).get("comparisonOnly")) for run in active_runs)
            conversation.status = ConversationStatus.WAITING.value if active_work else (
                ConversationStatus.COMPLETED.value if status == ReviewTaskStatus.RESOLVED else ConversationStatus.ERROR.value)
            conversation.updated_at = now

        latest_run = self._run_for_review(task)
        if latest_run is not None:
            latest_run.status = (
                RunStatus.COMPLETED.value
                if status == ReviewTaskStatus.RESOLVED
                else RunStatus.FAILED.value
            )
            latest_run.human_review_required = False
            latest_run.finished_at = latest_run.finished_at or now
            latest_run.final_outcome = (
                "human_review_resolved"
                if status == ReviewTaskStatus.RESOLVED
                else "human_review_cancelled"
            )
            latest_run.summary_json = {
                **(latest_run.summary_json or {}),
                "humanReviewResolution": status.value,
                "humanNote": note,
            }
            projection = self._db.get(RunExecutionProjectionModel, latest_run.id)
            if projection is not None:
                projection.run_status = latest_run.status
                projection.current_phase = latest_run.status
                projection.active_actor_name = None
                projection.active_node_id = None
                projection.state_json = {**(projection.state_json or {}),
                                         "humanReviewRequired": False, "finalOutcome": latest_run.final_outcome}
                projection.updated_at = now

        self._db.flush()
        review_event = EventService(self._db).record_event(
            conversation_id=task.conversation_id,
            message_id=task.message_id,
            event_type=ProcessingEventType.ACTOR_COMPLETED,
            actor_name="human_reviewer",
            correlation_id=message.correlation_id if message is not None else task.id,
            status=(
                ProcessingStatus.COMPLETED
                if status == ReviewTaskStatus.RESOLVED
                else ProcessingStatus.FAILED
            ),
            payload={
                "source": "human_review",
                "reviewTaskId": str(task.id),
                "resolutionStatus": status.value,
                "resolvedBy": resolved_by,
                "note": note,
                "runId": str(latest_run.id) if latest_run is not None else None,
            },
            commit=False,
            publish=False,
        )
        self._db.commit()
        self._db.refresh(task)
        event_bus.publish(review_event)
        return review_task_to_schema(task)

    def _has_open_reviews(self, conversation_id: UUID, *, exclude_id: UUID) -> bool:
        statement = (
            select(ReviewTaskModel.id)
            .where(
                ReviewTaskModel.conversation_id == conversation_id,
                ReviewTaskModel.id != exclude_id,
                ReviewTaskModel.status.in_(
                    [ReviewTaskStatus.OPEN.value, ReviewTaskStatus.IN_REVIEW.value]
                ),
            )
            .limit(1)
        )
        return self._db.scalars(statement).first() is not None

    def _run_for_review(self, task: ReviewTaskModel) -> RunModel | None:
        run_id = (task.metadata_json or {}).get("runtimeRunId")
        try:
            run = self._db.get(RunModel, UUID(str(run_id))) if run_id else None
        except (ValueError, TypeError):
            run = None
        if run is not None and run.message_id == task.message_id and not bool((run.experiment_json or {}).get("comparisonOnly")):
            return run
        statement = (
            select(RunModel)
            .where(RunModel.message_id == task.message_id)
            .order_by(RunModel.created_at.desc(), RunModel.id.desc())
        )
        return next((run for run in self._db.scalars(statement)
                     if not bool((run.experiment_json or {}).get("comparisonOnly"))), None)
