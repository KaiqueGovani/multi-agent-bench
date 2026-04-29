from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.mappers import (
    run_execution_event_to_schema,
    run_execution_projection_to_schema,
)
from app.db.models import (
    ConversationModel,
    MessageModel,
    ReviewTaskModel,
    RunExecutionEventModel,
    RunExecutionProjectionModel,
    RunModel,
)
from app.schemas.domain import JsonObject, RunExecutionEvent, RunExecutionProjection
from app.schemas.enums import (
    ConversationStatus,
    MessageDirection,
    MessageStatus,
    ProcessingEventType,
    ProcessingStatus,
    ReviewTaskStatus,
)
from app.services.event_bus import run_execution_bus
from app.services.events import EventService


class RunExecutionService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_run_execution_events(self, run_id: UUID) -> list[RunExecutionEvent]:
        statement = (
            select(RunExecutionEventModel)
            .where(RunExecutionEventModel.run_id == run_id)
            .order_by(RunExecutionEventModel.sequence_no, RunExecutionEventModel.created_at, RunExecutionEventModel.id)
        )
        return [
            run_execution_event_to_schema(model)
            for model in self._db.scalars(statement).all()
        ]

    def get_run_execution_projection(self, run_id: UUID) -> RunExecutionProjection | None:
        model = self._db.get(RunExecutionProjectionModel, run_id)
        if model is None:
            return None
        return run_execution_projection_to_schema(model)

    def get_by_external_event_id(
        self,
        *,
        run_id: UUID,
        external_event_id: str,
    ) -> RunExecutionEvent | None:
        statement = (
            select(RunExecutionEventModel)
            .where(
                RunExecutionEventModel.run_id == run_id,
                RunExecutionEventModel.external_event_id == external_event_id,
            )
            .limit(1)
        )
        model = self._db.scalars(statement).first()
        return run_execution_event_to_schema(model) if model else None

    def record_event(
        self,
        *,
        run_id: UUID,
        conversation_id: UUID,
        message_id: UUID,
        correlation_id: UUID,
        event_family: str,
        event_name: str,
        status: ProcessingStatus,
        payload: JsonObject | None = None,
        actor_name: str | None = None,
        node_id: str | None = None,
        tool_name: str | None = None,
        source: str | None = None,
        external_event_id: str | None = None,
        duration_ms: int | None = None,
    ) -> RunExecutionEvent:
        if external_event_id:
            existing = self.get_by_external_event_id(
                run_id=run_id,
                external_event_id=external_event_id,
            )
            if existing is not None:
                return existing

        sequence_no = self._next_sequence(run_id)
        payload_json = payload or {}
        model = RunExecutionEventModel(
            id=uuid4(),
            run_id=run_id,
            conversation_id=conversation_id,
            message_id=message_id,
            correlation_id=correlation_id,
            event_family=event_family,
            event_name=event_name,
            sequence_no=sequence_no,
            actor_name=actor_name,
            node_id=node_id,
            tool_name=tool_name,
            source=source,
            external_event_id=external_event_id,
            payload_json=payload_json,
            created_at=datetime.now(UTC),
            duration_ms=duration_ms,
            status=status.value,
        )
        self._db.add(model)
        self._db.flush()
        self._upsert_projection(model)
        self._sync_domain_state(model)
        self._db.commit()
        self._db.refresh(model)
        event = run_execution_event_to_schema(model)
        run_execution_bus.publish(event)
        self._derive_public_event(event)
        return event

    def _next_sequence(self, run_id: UUID) -> int:
        current = self._db.scalar(
            select(func.max(RunExecutionEventModel.sequence_no))
            .where(RunExecutionEventModel.run_id == run_id)
        )
        return int(current or 0) + 1

    def _upsert_projection(self, event: RunExecutionEventModel) -> None:
        run = self._db.get(RunModel, event.run_id)
        if run is None:
            return
        projection = self._db.get(RunExecutionProjectionModel, event.run_id)
        if projection is None:
            projection = RunExecutionProjectionModel(
                run_id=event.run_id,
                conversation_id=event.conversation_id,
                message_id=event.message_id,
                architecture_mode=(run.experiment_json or {}).get("architectureKey", "unknown"),
                run_status=run.status,
                architecture_view_json={},
                metrics_json={},
                state_json={},
            )
            self._db.add(projection)
            self._db.flush()

        architecture_view = dict(projection.architecture_view_json or {})
        metrics = dict(projection.metrics_json or {})
        state = dict(projection.state_json or {})

        actors = dict(architecture_view.get("actors") or {})
        if event.actor_name:
            actor_entry = dict(actors.get(event.actor_name) or {})
            actor_entry.update(
                {
                    "actorName": event.actor_name,
                    "lastEventName": event.event_name,
                    "lastStatus": event.status,
                    "nodeId": event.node_id,
                    "toolName": event.tool_name,
                    "updatedAt": event.created_at.isoformat(),
                }
            )
            actors[event.actor_name] = actor_entry
        architecture_view["actors"] = actors

        handoffs = list(architecture_view.get("handoffs") or [])
        if event.event_family == "handoff":
            handoffs.append(
                {
                    "eventId": str(event.id),
                    "actorName": event.actor_name,
                    "nodeId": event.node_id,
                    "status": event.status,
                    "payload": event.payload_json,
                }
            )
        architecture_view["handoffs"] = handoffs[-24:]

        stages = list(architecture_view.get("stages") or [])
        stage_name = str(
            event.payload_json.get("stage")
            or event.payload_json.get("phase")
            or event.event_name
        )
        if event.event_family in {"run", "node", "tool", "model", "review", "response"}:
            stages.append(
                {
                    "sequenceNo": event.sequence_no,
                    "eventFamily": event.event_family,
                    "eventName": event.event_name,
                    "stage": stage_name,
                    "actorName": event.actor_name,
                    "nodeId": event.node_id,
                    "status": event.status,
                    "createdAt": event.created_at.isoformat(),
                }
            )
        architecture_view["stages"] = stages[-64:]

        metrics["eventCount"] = int(metrics.get("eventCount", 0)) + 1
        metrics["toolCallCount"] = int(metrics.get("toolCallCount", 0)) + (
            1 if event.event_family == "tool" and event.event_name.endswith("started") else 0
        )
        metrics["handoffCount"] = int(metrics.get("handoffCount", 0)) + (
            1 if event.event_family == "handoff" else 0
        )
        if isinstance(event.duration_ms, int):
            metrics["lastDurationMs"] = event.duration_ms
        if "tokenUsage" in event.payload_json:
            metrics["tokenUsage"] = event.payload_json["tokenUsage"]

        state.update(
            {
                "lastEventId": str(event.id),
                "lastEventFamily": event.event_family,
                "lastEventName": event.event_name,
                "lastPayload": event.payload_json,
                "lastStatus": event.status,
            }
        )

        projection.run_status = run.status
        projection.active_node_id = (
            event.node_id if event.status == ProcessingStatus.RUNNING.value else projection.active_node_id
        )
        projection.active_actor_name = (
            event.actor_name if event.status == ProcessingStatus.RUNNING.value else projection.active_actor_name
        )
        projection.current_phase = stage_name
        projection.source = event.source
        projection.architecture_view_json = architecture_view
        projection.metrics_json = metrics
        projection.state_json = state
        projection.updated_at = datetime.now(UTC)
        self._db.flush()

    def _sync_domain_state(self, event: RunExecutionEventModel) -> None:
        run = self._db.get(RunModel, event.run_id)
        message = self._db.get(MessageModel, event.message_id)
        conversation = self._db.get(ConversationModel, event.conversation_id)
        if run is None or message is None or conversation is None:
            return

        now = datetime.now(UTC)
        payload = event.payload_json or {}

        if event.event_family == "run" and event.event_name == "started":
            message.status = MessageStatus.PROCESSING.value
            conversation.status = ConversationStatus.WAITING.value
            conversation.updated_at = now
            if run.started_at is None:
                run.started_at = now

        if event.event_family == "review" and event.event_name == "required":
            review_task = self._ensure_review_task(event, payload)
            payload.setdefault("reviewTaskId", str(review_task.id))
            message.status = MessageStatus.HUMAN_REVIEW_REQUIRED.value
            conversation.status = ConversationStatus.HUMAN_REVIEW_REQUIRED.value
            conversation.updated_at = now

        if event.event_family == "response" and event.event_name == "final":
            review_required = bool(payload.get("reviewRequired"))
            outbound_message = self._ensure_outbound_message(
                event=event,
                content_text=str(payload.get("contentText") or "").strip(),
                review_required=review_required,
            )
            payload.setdefault("messageId", str(outbound_message.id))
            message.metadata_json = {
                **(message.metadata_json or {}),
                "reviewRequired": review_required,
                "lastRuntimeRunId": str(event.run_id),
                "lastResponseMessageId": str(outbound_message.id),
            }
            if review_required:
                message.status = MessageStatus.HUMAN_REVIEW_REQUIRED.value
            else:
                message.status = MessageStatus.COMPLETED.value
                if conversation.status != ConversationStatus.HUMAN_REVIEW_REQUIRED.value:
                    conversation.status = ConversationStatus.COMPLETED.value
            conversation.updated_at = now

        if event.event_family == "run" and event.event_name == "completed":
            review_required = bool(payload.get("reviewRequired") or run.human_review_required)
            message.metadata_json = {
                **(message.metadata_json or {}),
                "processingEndAt": now.isoformat(),
                "reviewRequired": review_required,
                "totalDurationMs": event.duration_ms,
            }
            if review_required:
                message.status = MessageStatus.HUMAN_REVIEW_REQUIRED.value
                conversation.status = ConversationStatus.HUMAN_REVIEW_REQUIRED.value
            else:
                if message.status != MessageStatus.HUMAN_REVIEW_REQUIRED.value:
                    message.status = MessageStatus.COMPLETED.value
                if conversation.status != ConversationStatus.HUMAN_REVIEW_REQUIRED.value:
                    conversation.status = ConversationStatus.COMPLETED.value
            conversation.updated_at = now

        if event.status == ProcessingStatus.FAILED.value or (
            event.event_family == "run" and event.event_name == "failed"
        ):
            message.status = MessageStatus.ERROR.value
            conversation.status = ConversationStatus.ERROR.value
            conversation.updated_at = now

        self._db.flush()

    def _ensure_outbound_message(
        self,
        *,
        event: RunExecutionEventModel,
        content_text: str,
        review_required: bool,
    ) -> MessageModel:
        statement = (
            select(MessageModel)
            .where(
                MessageModel.conversation_id == event.conversation_id,
                MessageModel.correlation_id == event.correlation_id,
                MessageModel.direction == MessageDirection.OUTBOUND.value,
            )
            .order_by(MessageModel.created_at_server.desc(), MessageModel.id.desc())
            .limit(1)
        )
        outbound = self._db.scalars(statement).first()
        run = self._db.get(RunModel, event.run_id)
        architecture_mode = (run.experiment_json or {}).get("architectureKey", "unknown") if run else "unknown"
        if outbound is None:
            outbound = MessageModel(
                id=uuid4(),
                conversation_id=event.conversation_id,
                direction=MessageDirection.OUTBOUND.value,
                content_text=content_text or "Runtime completed without textual response.",
                created_at_server=datetime.now(UTC),
                status=MessageStatus.COMPLETED.value,
                correlation_id=event.correlation_id,
                metadata_json={
                    "architectureMode": architecture_mode,
                    "reviewRequired": review_required,
                    "runtimeRunId": str(event.run_id),
                    "source": event.source or "ai_service",
                },
            )
            self._db.add(outbound)
        else:
            outbound.content_text = content_text or outbound.content_text
            outbound.status = MessageStatus.COMPLETED.value
            outbound.metadata_json = {
                **(outbound.metadata_json or {}),
                "architectureMode": architecture_mode,
                "reviewRequired": review_required,
                "runtimeRunId": str(event.run_id),
                "source": event.source or "ai_service",
            }
        self._db.flush()
        return outbound

    def _ensure_review_task(
        self,
        event: RunExecutionEventModel,
        payload: JsonObject,
    ) -> ReviewTaskModel:
        statement = (
            select(ReviewTaskModel)
            .where(
                ReviewTaskModel.conversation_id == event.conversation_id,
                ReviewTaskModel.message_id == event.message_id,
                ReviewTaskModel.status.in_(
                    [ReviewTaskStatus.OPEN.value, ReviewTaskStatus.IN_REVIEW.value]
                ),
            )
            .order_by(ReviewTaskModel.created_at.desc(), ReviewTaskModel.id.desc())
            .limit(1)
        )
        review_task = self._db.scalars(statement).first()
        if review_task is not None:
            review_task.metadata_json = {
                **(review_task.metadata_json or {}),
                "runtimeRunId": str(event.run_id),
                "source": event.source or "ai_service",
            }
            self._db.flush()
            return review_task

        review_task = ReviewTaskModel(
            id=uuid4(),
            conversation_id=event.conversation_id,
            message_id=event.message_id,
            reason=str(payload.get("reason") or "Runtime requested human review."),
            status=ReviewTaskStatus.OPEN.value,
            metadata_json={
                **payload,
                "runtimeRunId": str(event.run_id),
                "source": event.source or "ai_service",
            },
        )
        self._db.add(review_task)
        self._db.flush()
        return review_task

    def _derive_public_event(self, event: RunExecutionEvent) -> None:
        mapping = {
            ("run", "started"): ProcessingEventType.PROCESSING_STARTED,
            ("node", "started"): ProcessingEventType.ACTOR_INVOKED,
            ("node", "progress"): ProcessingEventType.ACTOR_PROGRESS,
            ("node", "completed"): ProcessingEventType.ACTOR_COMPLETED,
            ("node", "failed"): ProcessingEventType.ACTOR_FAILED,
            ("handoff", "requested"): ProcessingEventType.HANDOFF_REQUESTED,
            ("review", "required"): ProcessingEventType.REVIEW_REQUIRED,
            ("response", "partial"): ProcessingEventType.RESPONSE_PARTIAL,
            ("response", "final"): ProcessingEventType.RESPONSE_FINAL,
            ("run", "completed"): ProcessingEventType.PROCESSING_COMPLETED,
            ("run", "failed"): ProcessingEventType.ACTOR_FAILED,
        }
        public_type = mapping.get((event.event_family, event.event_name))
        if public_type is None:
            if event.event_family == "tool":
                public_type = ProcessingEventType.ACTOR_PROGRESS
            elif event.event_family == "model":
                public_type = ProcessingEventType.ACTOR_PROGRESS
            else:
                return

        EventService(self._db).record_event(
            conversation_id=event.conversation_id,
            message_id=event.message_id,
            event_type=public_type,
            actor_name=event.actor_name,
            correlation_id=event.correlation_id,
            status=event.status,
            payload={
                **event.payload,
                "runId": str(event.run_id),
                "eventFamily": event.event_family,
                "eventName": event.event_name,
                "nodeId": event.node_id,
                "toolName": event.tool_name,
                "source": event.source or "ai_service",
                "sequenceNo": event.sequence_no,
            },
            duration_ms=event.duration_ms,
        )
