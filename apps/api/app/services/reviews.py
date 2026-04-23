from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.mappers import review_task_to_schema
from app.db.models import ConversationModel, MessageModel, ReviewTaskModel, RunModel
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
            EventService(self._db).record_event(
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
            return review_task_to_schema(task)

        message = self._db.get(MessageModel, task.message_id)
        if message is not None:
            message.status = (
                MessageStatus.COMPLETED.value
                if status == ReviewTaskStatus.RESOLVED
                else MessageStatus.ERROR.value
            )

        conversation = self._db.get(ConversationModel, task.conversation_id)
        if conversation is not None and not self._has_open_reviews(task.conversation_id, exclude_id=task.id):
            conversation.status = (
                ConversationStatus.COMPLETED.value
                if status == ReviewTaskStatus.RESOLVED
                else ConversationStatus.ERROR.value
            )
            conversation.updated_at = now

        latest_run = self._latest_run_for_message(task.message_id)
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

        self._db.flush()
        EventService(self._db).record_event(
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

    def _latest_run_for_message(self, message_id: UUID) -> RunModel | None:
        statement = (
            select(RunModel)
            .where(RunModel.message_id == message_id)
            .order_by(RunModel.created_at.desc(), RunModel.id.desc())
            .limit(1)
        )
        return self._db.scalars(statement).first()
