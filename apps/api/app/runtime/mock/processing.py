import random
import time
import unicodedata
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AttachmentModel, ConversationModel, MessageModel, ReviewTaskModel
from app.schemas.domain import ProcessingEvent
from app.db.session import SessionLocal
from app.schemas.enums import (
    ArchitectureMode,
    ConversationStatus,
    MessageDirection,
    MessageStatus,
    ProcessingEventType,
    ProcessingStatus,
    ReviewTaskStatus,
)
from app.services.events import EventService
from app.services.run_execution import RunExecutionService


STOCK_CATALOG = {
    "dipirona": {"available": True, "quantity": 17, "unit": "frascos"},
    "ibuprofeno": {"available": True, "quantity": 9, "unit": "caixas"},
    "amoxicilina": {"available": False, "quantity": 0, "unit": "caixas"},
    "paracetamol": {"available": True, "quantity": 23, "unit": "caixas"},
    "omeprazol": {"available": True, "quantity": 5, "unit": "caixas"},
    "loratadina": {"available": True, "quantity": 12, "unit": "caixas"},
    "azitromicina": {"available": False, "quantity": 0, "unit": "caixas"},
    "rivotril": {"available": False, "quantity": 0, "unit": "caixas"},
    "insulina": {"available": True, "quantity": 2, "unit": "frascos"},
}

STOCK_TERMS = ["tem ", "estoque", "disponivel", "disponibilidade", "preco", "quanto custa"]


class MockProcessingRuntime:
    def __init__(self, step_delay_seconds: float | None = None) -> None:
        self._settings = get_settings()
        self._step_delay_seconds = (
            step_delay_seconds
            if step_delay_seconds is not None
            else self._settings.mock_runtime_step_delay_seconds
        )

    def process_message(
        self,
        *,
        conversation_id: UUID,
        message_id: UUID,
        correlation_id: UUID,
        run_id: UUID | None = None,
        architecture_mode: str | None = None,
        comparison_only: bool = False,
    ) -> bool:
        with SessionLocal() as db:
            message = db.get(MessageModel, message_id)
            if message is None:
                return False

            event_service = EventService(db)
            started_at = datetime.now(UTC)
            resolved_architecture_mode = architecture_mode or self._settings.default_architecture_mode
            event_context = self._event_context(message, resolved_architecture_mode)
            context_text = self._contextual_query_text(db, message, resolved_architecture_mode)
            review_required = self._requires_review(message)

            if comparison_only:
                if run_id is None:
                    raise ValueError("run_id is required for comparison-only processing")
                self._process_comparison_run(
                    db,
                    run_id=run_id,
                    conversation_id=conversation_id,
                    message=message,
                    correlation_id=correlation_id,
                    architecture_mode=resolved_architecture_mode,
                    event_context=event_context,
                    review_required=review_required,
                    started_at=started_at,
                )
                return review_required

            message.status = MessageStatus.PROCESSING.value
            db.commit()

            self._record(
                event_service,
                conversation_id=conversation_id,
                message_id=message_id,
                correlation_id=correlation_id,
                event_type=ProcessingEventType.PROCESSING_STARTED,
                status=ProcessingStatus.RUNNING,
                payload=self._base_payload({"messageId": str(message_id)}, event_context),
            )

            route = self._select_route(db, message, context_text)
            self._invoke_actor(
                db,
                event_service,
                conversation_id=conversation_id,
                message_id=message_id,
                correlation_id=correlation_id,
                actor_name="router_agent",
                reason="classifying incoming request",
                result={"route": route},
                event_context=event_context,
            )

            selected_actor = self._select_actor(db, message, context_text, route=route)
            self._invoke_actor(
                db,
                event_service,
                conversation_id=conversation_id,
                message_id=message_id,
                correlation_id=correlation_id,
                actor_name=selected_actor,
                reason="handling request with mocked domain actor",
                result={"handledBy": selected_actor},
                event_context=event_context,
            )

            self._invoke_actor(
                db,
                event_service,
                conversation_id=conversation_id,
                message_id=message_id,
                correlation_id=correlation_id,
                actor_name="supervisor_agent",
                reason="checking mocked response before final answer",
                result={"reviewRequired": review_required},
                event_context=event_context,
            )

            if review_required:
                self._create_review_task(
                    db,
                    event_service,
                    conversation_id=conversation_id,
                    message_id=message_id,
                    correlation_id=correlation_id,
                    event_context=event_context,
                )

            outbound_message = self._create_outbound_message(
                db,
                inbound_message=message,
                correlation_id=correlation_id,
                review_required=review_required,
                architecture_mode=resolved_architecture_mode,
                context_text=context_text,
                route=route,
                run_id=run_id,
            )

            self._record(
                event_service,
                conversation_id=conversation_id,
                message_id=message_id,
                correlation_id=correlation_id,
                event_type=ProcessingEventType.RESPONSE_FINAL,
                actor_name="supervisor_agent",
                status=ProcessingStatus.COMPLETED,
                payload=self._base_payload(
                    {
                        "messageId": str(outbound_message.id),
                        "contentText": outbound_message.content_text,
                        "reviewRequired": review_required,
                    },
                    event_context,
                ),
            )

            total_duration_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
            completed_at = datetime.now(UTC)
            message.metadata_json = {
                **(message.metadata_json or {}),
                "processingStartAt": started_at.isoformat(),
                "processingEndAt": completed_at.isoformat(),
                "reviewRequired": review_required,
                "totalDurationMs": total_duration_ms,
            }
            message.status = (
                MessageStatus.HUMAN_REVIEW_REQUIRED.value
                if review_required
                else MessageStatus.COMPLETED.value
            )
            db.commit()

            self._record(
                event_service,
                conversation_id=conversation_id,
                message_id=message_id,
                correlation_id=correlation_id,
                event_type=ProcessingEventType.PROCESSING_COMPLETED,
                status=ProcessingStatus.COMPLETED,
                duration_ms=total_duration_ms,
                payload=self._base_payload(
                    {
                        "totalDurationMs": total_duration_ms,
                        "runtimeMode": self._settings.runtime_mode,
                    },
                    event_context,
                ),
            )

            # Emit run-execution telemetry for the primary run so its projection (metrics + flow)
            # matches the comparison runs. suppress_public_events=True keeps the main flow above
            # the SOLE source of the outbound message and conversation events (no duplicates).
            if run_id is not None:
                saved_delay = self._step_delay_seconds
                self._step_delay_seconds = 0
                try:
                    self._process_comparison_run(
                        db,
                        run_id=run_id,
                        conversation_id=conversation_id,
                        message=message,
                        correlation_id=correlation_id,
                        architecture_mode=resolved_architecture_mode,
                        event_context=event_context,
                        review_required=review_required,
                        started_at=started_at,
                        suppress_public_events=True,
                    )
                finally:
                    self._step_delay_seconds = saved_delay

            return review_required

    def _process_comparison_run(
        self,
        db: Session,
        *,
        run_id: UUID,
        conversation_id: UUID,
        message: MessageModel,
        correlation_id: UUID,
        architecture_mode: str,
        event_context: dict,
        review_required: bool,
        started_at: datetime,
        suppress_public_events: bool = False,
    ) -> None:
        run_execution = RunExecutionService(db)
        self._record_run_event(
            run_execution,
            run_id=run_id,
            conversation_id=conversation_id,
            message_id=message.id,
            correlation_id=correlation_id,
            event_family="run",
            event_name="started",
            status=ProcessingStatus.RUNNING,
            payload=self._base_payload({"phase": "dispatch"}, event_context),
            suppress_public_events=suppress_public_events,
        )

        context_text = self._contextual_query_text(db, message, architecture_mode)
        route = self._select_route(db, message, context_text)
        selected_actor = self._select_actor(db, message, context_text, route=route)
        tool_calls = self._TOOL_COUNTS.get(architecture_mode, 2)

        if architecture_mode == ArchitectureMode.STRUCTURED_WORKFLOW.value:
            self._simulate_run_node(
                db,
                run_execution,
                run_id=run_id,
                conversation_id=conversation_id,
                message_id=message.id,
                correlation_id=correlation_id,
                actor_name="router_agent",
                node_id="classify.router_agent",
                stage="classify",
                result={"route": route},
                event_context=event_context,
                suppress_public_events=suppress_public_events,
            )
            self._simulate_run_node(
                db,
                run_execution,
                run_id=run_id,
                conversation_id=conversation_id,
                message_id=message.id,
                correlation_id=correlation_id,
                actor_name="workflow_evidence_agent",
                node_id="gather_evidence.workflow_evidence_agent",
                stage="gather_evidence",
                result={"handledBy": selected_actor, "route": route},
                event_context=event_context,
                suppress_public_events=suppress_public_events,
            )
            self._simulate_tool_call(
                run_execution,
                run_id=run_id,
                conversation_id=conversation_id,
                message_id=message.id,
                correlation_id=correlation_id,
                actor_name="workflow_evidence_agent",
                node_id="gather_evidence.workflow_evidence_agent",
                route=route,
                event_context=event_context,
                count=tool_calls,
                suppress_public_events=suppress_public_events,
            )
            if self._has_attachments(db, message.id):
                self._simulate_run_node(
                    db,
                    run_execution,
                    run_id=run_id,
                    conversation_id=conversation_id,
                    message_id=message.id,
                    correlation_id=correlation_id,
                    actor_name="workflow_multimodal_agent",
                    node_id="multimodal_analysis.workflow_multimodal_agent",
                    stage="multimodal_analysis",
                    result={"attachmentsAnalyzed": True},
                    event_context=event_context,
                    suppress_public_events=suppress_public_events,
                )
            if review_required:
                self._simulate_run_node(
                    db,
                    run_execution,
                    run_id=run_id,
                    conversation_id=conversation_id,
                    message_id=message.id,
                    correlation_id=correlation_id,
                    actor_name="workflow_review_agent",
                    node_id="review_gate.workflow_review_agent",
                    stage="review_gate",
                    result={"reviewRequired": True},
                    event_context=event_context,
                    suppress_public_events=suppress_public_events,
                )
            final_actor = "workflow_synthesis_agent"
            self._simulate_run_node(
                db,
                run_execution,
                run_id=run_id,
                conversation_id=conversation_id,
                message_id=message.id,
                correlation_id=correlation_id,
                actor_name=final_actor,
                node_id="synthesize.workflow_synthesis_agent",
                stage="synthesize",
                result={"reviewRequired": review_required},
                event_context=event_context,
                suppress_public_events=suppress_public_events,
            )
        elif architecture_mode == ArchitectureMode.DECENTRALIZED_SWARM.value:
            final_actor = "swarm_synthesizer"
            self._simulate_run_node(
                db,
                run_execution,
                run_id=run_id,
                conversation_id=conversation_id,
                message_id=message.id,
                correlation_id=correlation_id,
                actor_name="swarm_coordinator",
                node_id="handoff_loop.swarm_coordinator",
                stage="handoff_loop",
                result={"route": route},
                event_context=event_context,
                suppress_public_events=suppress_public_events,
            )
            self._record_run_event(
                run_execution,
                run_id=run_id,
                conversation_id=conversation_id,
                message_id=message.id,
                correlation_id=correlation_id,
                event_family="handoff",
                event_name="requested",
                status=ProcessingStatus.COMPLETED,
                actor_name="swarm_coordinator",
                node_id="handoff_loop.swarm_coordinator",
                payload=self._base_payload(
                    {"from": "swarm_coordinator", "to": selected_actor, "route": route},
                    event_context,
                ),
                suppress_public_events=suppress_public_events,
            )
            self._simulate_run_node(
                db,
                run_execution,
                run_id=run_id,
                conversation_id=conversation_id,
                message_id=message.id,
                correlation_id=correlation_id,
                actor_name=selected_actor,
                node_id=f"specialist.{selected_actor}",
                stage="specialist",
                result={"handledBy": selected_actor},
                event_context=event_context,
                suppress_public_events=suppress_public_events,
            )
            self._simulate_tool_call(
                run_execution,
                run_id=run_id,
                conversation_id=conversation_id,
                message_id=message.id,
                correlation_id=correlation_id,
                actor_name=selected_actor,
                node_id=f"specialist.{selected_actor}",
                route=route,
                event_context=event_context,
                count=tool_calls,
                suppress_public_events=suppress_public_events,
            )
            self._record_run_event(
                run_execution,
                run_id=run_id,
                conversation_id=conversation_id,
                message_id=message.id,
                correlation_id=correlation_id,
                event_family="handoff",
                event_name="requested",
                status=ProcessingStatus.COMPLETED,
                actor_name=selected_actor,
                node_id=f"specialist.{selected_actor}",
                payload=self._base_payload(
                    {"from": selected_actor, "to": final_actor, "route": route},
                    event_context,
                ),
                suppress_public_events=suppress_public_events,
            )
            self._simulate_run_node(
                db,
                run_execution,
                run_id=run_id,
                conversation_id=conversation_id,
                message_id=message.id,
                correlation_id=correlation_id,
                actor_name=final_actor,
                node_id="synthesize.swarm_synthesizer",
                stage="synthesize",
                result={"reviewRequired": review_required},
                event_context=event_context,
                suppress_public_events=suppress_public_events,
            )
        else:
            final_actor = "response_streamer"
            self._simulate_run_node(
                db,
                run_execution,
                run_id=run_id,
                conversation_id=conversation_id,
                message_id=message.id,
                correlation_id=correlation_id,
                actor_name="supervisor_agent",
                node_id="dispatch.supervisor_agent",
                stage="dispatch",
                result={"route": route},
                event_context=event_context,
                suppress_public_events=suppress_public_events,
            )
            self._simulate_run_node(
                db,
                run_execution,
                run_id=run_id,
                conversation_id=conversation_id,
                message_id=message.id,
                correlation_id=correlation_id,
                actor_name=selected_actor,
                node_id=f"specialist.{selected_actor}",
                stage="specialist",
                result={"handledBy": selected_actor},
                event_context=event_context,
                suppress_public_events=suppress_public_events,
            )
            self._simulate_tool_call(
                run_execution,
                run_id=run_id,
                conversation_id=conversation_id,
                message_id=message.id,
                correlation_id=correlation_id,
                actor_name=selected_actor,
                node_id=f"specialist.{selected_actor}",
                route=route,
                event_context=event_context,
                count=tool_calls,
                suppress_public_events=suppress_public_events,
            )
            self._simulate_run_node(
                db,
                run_execution,
                run_id=run_id,
                conversation_id=conversation_id,
                message_id=message.id,
                correlation_id=correlation_id,
                actor_name=final_actor,
                node_id="response_streamer.completed",
                stage="synthesize",
                result={"reviewRequired": review_required},
                event_context=event_context,
                suppress_public_events=suppress_public_events,
            )

        if review_required:
            self._record_run_event(
                run_execution,
                run_id=run_id,
                conversation_id=conversation_id,
                message_id=message.id,
                correlation_id=correlation_id,
                event_family="review",
                event_name="required",
                status=ProcessingStatus.HUMAN_REVIEW_REQUIRED,
                actor_name=final_actor,
                node_id=f"{final_actor}.review",
                payload=self._base_payload(
                    {
                        "reason": "Mocked scenario requested human review",
                        "reviewRequired": True,
                    },
                    event_context,
                ),
                suppress_public_events=suppress_public_events,
            )

        total_duration_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
        token_usage = self._mock_token_usage(architecture_mode)

        # For comparison-only runs, the run-execution domain sync is skipped
        # (see RunExecutionService._is_comparison_only), so we explicitly
        # persist a per-run outbound message here. This lets the UI display
        # the response of every architecture in a multi-architecture run,
        # not just the canonical one.
        if not suppress_public_events:
            self._create_outbound_message(
                db,
                inbound_message=message,
                correlation_id=correlation_id,
                review_required=review_required,
                architecture_mode=architecture_mode,
                context_text=context_text,
                route=route,
                run_id=run_id,
            )

        self._record_run_event(
            run_execution,
            run_id=run_id,
            conversation_id=conversation_id,
            message_id=message.id,
            correlation_id=correlation_id,
            event_family="response",
            event_name="final",
            status=ProcessingStatus.COMPLETED,
            actor_name=final_actor,
            node_id=f"{final_actor}.final",
            payload=self._base_payload(
                {
                    "contentText": self._build_response_text(review_required, context_text, route=route),
                    "reviewRequired": review_required,
                    "route": route,
                    "finalActor": final_actor,
                    "tokenUsage": token_usage,
                },
                event_context,
            ),
            suppress_public_events=suppress_public_events,
        )
        self._record_run_event(
            run_execution,
            run_id=run_id,
            conversation_id=conversation_id,
            message_id=message.id,
            correlation_id=correlation_id,
            event_family="run",
            event_name="completed",
            status=ProcessingStatus.COMPLETED,
            duration_ms=total_duration_ms,
            payload=self._base_payload(
                {
                    "phase": "completed",
                    "reviewRequired": review_required,
                    "runtimeMode": self._settings.runtime_mode,
                    "totalDurationMs": total_duration_ms,
                },
                event_context,
            ),
            suppress_public_events=suppress_public_events,
        )

    def _invoke_actor(
        self,
        db: Session,
        event_service: EventService,
        *,
        conversation_id: UUID,
        message_id: UUID,
        correlation_id: UUID,
        actor_name: str,
        reason: str,
        result: dict,
        event_context: dict,
    ) -> None:
        started_at = datetime.now(UTC)
        invoked_event = self._record(
            event_service,
            conversation_id=conversation_id,
            message_id=message_id,
            correlation_id=correlation_id,
            event_type=ProcessingEventType.ACTOR_INVOKED,
            actor_name=actor_name,
            status=ProcessingStatus.RUNNING,
            payload=self._base_payload({"reason": reason}, event_context),
        )
        time.sleep(self._step_delay_seconds / 2)
        self._record(
            event_service,
            conversation_id=conversation_id,
            message_id=message_id,
            correlation_id=correlation_id,
            event_type=ProcessingEventType.ACTOR_PROGRESS,
            actor_name=actor_name,
            parent_event_id=invoked_event.id,
            status=ProcessingStatus.RUNNING,
            payload=self._base_payload(
                {
                    "step": "mock_processing",
                    "message": "Actor is processing the mocked task.",
                    "progressPercent": 50,
                    "actorName": actor_name,
                },
                event_context,
            ),
        )
        time.sleep(self._step_delay_seconds / 2)
        duration_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
        self._record(
            event_service,
            conversation_id=conversation_id,
            message_id=message_id,
            correlation_id=correlation_id,
            event_type=ProcessingEventType.ACTOR_COMPLETED,
            actor_name=actor_name,
            status=ProcessingStatus.COMPLETED,
            duration_ms=duration_ms,
            payload=self._base_payload(result | {"durationMs": duration_ms}, event_context),
        )
        db.expire_all()

    def _simulate_run_node(
        self,
        db: Session,
        run_execution: RunExecutionService,
        *,
        run_id: UUID,
        conversation_id: UUID,
        message_id: UUID,
        correlation_id: UUID,
        actor_name: str,
        node_id: str,
        stage: str,
        result: dict,
        event_context: dict,
        suppress_public_events: bool = False,
    ) -> None:
        started_at = datetime.now(UTC)
        self._record_run_event(
            run_execution,
            run_id=run_id,
            conversation_id=conversation_id,
            message_id=message_id,
            correlation_id=correlation_id,
            event_family="node",
            event_name="started",
            status=ProcessingStatus.RUNNING,
            actor_name=actor_name,
            node_id=node_id,
            payload=self._base_payload({"phase": stage}, event_context),
            suppress_public_events=suppress_public_events,
        )
        time.sleep(self._step_delay_seconds / 2)
        self._record_run_event(
            run_execution,
            run_id=run_id,
            conversation_id=conversation_id,
            message_id=message_id,
            correlation_id=correlation_id,
            event_family="node",
            event_name="progress",
            status=ProcessingStatus.RUNNING,
            actor_name=actor_name,
            node_id=node_id,
            payload=self._base_payload(
                {
                    "phase": stage,
                    "message": "Actor is processing the mocked task.",
                    "progressPercent": 50,
                },
                event_context,
            ),
            suppress_public_events=suppress_public_events,
        )
        time.sleep(self._step_delay_seconds / 2)
        duration_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
        self._record_run_event(
            run_execution,
            run_id=run_id,
            conversation_id=conversation_id,
            message_id=message_id,
            correlation_id=correlation_id,
            event_family="node",
            event_name="completed",
            status=ProcessingStatus.COMPLETED,
            actor_name=actor_name,
            node_id=node_id,
            duration_ms=duration_ms,
            payload=self._base_payload(result | {"phase": stage, "durationMs": duration_ms}, event_context),
            suppress_public_events=suppress_public_events,
        )
        db.expire_all()

    def _record_run_event(
        self,
        run_execution: RunExecutionService,
        *,
        run_id: UUID,
        conversation_id: UUID,
        message_id: UUID,
        correlation_id: UUID,
        event_family: str,
        event_name: str,
        status: ProcessingStatus,
        payload: dict,
        actor_name: str | None = None,
        node_id: str | None = None,
        duration_ms: int | None = None,
        suppress_public_events: bool = False,
    ) -> None:
        run_execution.record_event(
            run_id=run_id,
            conversation_id=conversation_id,
            message_id=message_id,
            correlation_id=correlation_id,
            event_family=event_family,
            event_name=event_name,
            status=status,
            payload=payload,
            actor_name=actor_name,
            node_id=node_id,
            source="mock_runtime",
            duration_ms=duration_ms,
            suppress_public_events=suppress_public_events,
        )

    def _record(
        self,
        event_service: EventService,
        *,
        conversation_id: UUID,
        message_id: UUID,
        correlation_id: UUID,
        event_type: ProcessingEventType,
        status: ProcessingStatus,
        payload: dict,
        actor_name: str | None = None,
        parent_event_id: UUID | None = None,
        duration_ms: int | None = None,
    ) -> ProcessingEvent:
        return event_service.record_event(
            conversation_id=conversation_id,
            message_id=message_id,
            event_type=event_type,
            actor_name=actor_name,
            parent_event_id=parent_event_id,
            correlation_id=correlation_id,
            status=status,
            payload=payload,
            duration_ms=duration_ms,
        )

    def _create_outbound_message(
        self,
        db: Session,
        *,
        inbound_message: MessageModel,
        correlation_id: UUID,
        review_required: bool,
        architecture_mode: str,
        context_text: str | None = None,
        route: str | None = None,
        run_id: UUID | None = None,
    ) -> MessageModel:
        metadata: dict = {
            "channel": self._settings.default_channel,
            "architectureMode": architecture_mode,
            "runtimeMode": self._settings.runtime_mode,
            "reviewRequired": review_required,
        }
        if run_id is not None:
            metadata["runtimeRunId"] = str(run_id)
        outbound = MessageModel(
            id=uuid4(),
            conversation_id=inbound_message.conversation_id,
            direction=MessageDirection.OUTBOUND.value,
            content_text=self._build_response_text(
                review_required,
                context_text or inbound_message.content_text,
                route=route,
            ),
            created_at_server=datetime.now(UTC),
            status=MessageStatus.COMPLETED.value,
            correlation_id=correlation_id,
            metadata_json=metadata,
            model_context_json={
                "language": "pt-BR",
                "inferredIntent": self._infer_intent(context_text or inbound_message.content_text),
            },
        )
        db.add(outbound)
        db.commit()
        db.refresh(outbound)
        return outbound

    def _create_review_task(
        self,
        db: Session,
        event_service: EventService,
        *,
        conversation_id: UUID,
        message_id: UUID,
        correlation_id: UUID,
        event_context: dict,
    ) -> None:
        review_task = ReviewTaskModel(
            id=uuid4(),
            conversation_id=conversation_id,
            message_id=message_id,
            reason="Mocked scenario requested human review",
            status=ReviewTaskStatus.OPEN.value,
            metadata_json={
                **event_context,
                "runtimeMode": self._settings.runtime_mode,
            },
        )
        db.add(review_task)
        conversation = db.get(ConversationModel, conversation_id)
        if conversation is not None:
            conversation.status = ConversationStatus.HUMAN_REVIEW_REQUIRED.value
        db.flush()

        self._record(
            event_service,
            conversation_id=conversation_id,
            message_id=message_id,
            correlation_id=correlation_id,
            event_type=ProcessingEventType.REVIEW_REQUIRED,
            actor_name="supervisor_agent",
            status=ProcessingStatus.HUMAN_REVIEW_REQUIRED,
            payload=self._base_payload(
                {
                    "reason": review_task.reason,
                    "reviewTaskId": str(review_task.id),
                    "reviewRequired": True,
                },
                event_context,
            ),
        )

    def _select_route(self, db: Session, message: MessageModel, context_text: str | None = None) -> str:
        if self._has_attachments(db, message.id):
            return "image_intake"
        if self._looks_like_stock_question(message.content_text, context_text):
            return "stock_lookup"
        return "faq"

    def _select_actor(
        self,
        db: Session,
        message: MessageModel,
        context_text: str | None = None,
        *,
        route: str | None = None,
    ) -> str:
        route = route or self._select_route(db, message, context_text)
        if route == "image_intake":
            return "image_intake_agent"
        if route == "stock_lookup":
            return "stock_agent"
        return "faq_agent"

    @staticmethod
    def _build_response_text(
        review_required: bool,
        text: str | None = None,
        *,
        route: str | None = None,
    ) -> str:
        if review_required:
            return "Recebi sua solicitacao e encaminhei este caso para revisao humana simulada."
        if route in {None, "faq"} and _looks_like_opening_hours_question(text):
            return (
                "A farmacia funciona diariamente das 08:00 as 22:00 no contexto "
                "simulado da POC."
            )
        if route == "stock_lookup":
            product = _infer_product_name(text)
            item = STOCK_CATALOG.get(product)
            if item is not None and item["available"]:
                return (
                    f"Temos {item['quantity']} {item['unit']} de {product} "
                    "disponiveis no estoque simulado da POC."
                )
            if item is not None:
                return f"Nao encontrei {product} disponivel no estoque simulado da POC."
            return "Nao consegui identificar o produto no estoque simulado da POC."
        return (
            "Recebi sua solicitacao. Esta e uma resposta simulada da POC; "
            "nenhum agente real ou decisao farmaceutica foi executado."
        )

    def _infer_intent(self, text: str | None) -> str:
        if self._looks_like_review_request(text):
            return "human_review"
        if self._looks_like_stock_question(text):
            return "stock_availability"
        return "general_question"

    @staticmethod
    def _looks_like_stock_question(text: str | None, context_text: str | None = None) -> bool:
        latest = _normalize_text(text)
        context = _normalize_text(context_text)
        return _looks_like_stock_question_text(text) or (
            _infer_product_name(text) is not None
            and any(term in context for term in STOCK_TERMS)
            and len(latest.split()) <= 6
        )

    @staticmethod
    def _looks_like_review_request(text: str | None) -> bool:
        normalized = (text or "").lower()
        return any(
            term in normalized
            for term in [
                "revisao humana",
                "revisão humana",
                "supervisor",
                "farmaceutico",
                "farmacêutico",
            ]
        )

    def _requires_review(self, message: MessageModel) -> bool:
        metadata = message.metadata_json or {}
        return bool(metadata.get("forceReview")) or self._looks_like_review_request(
            message.content_text
        )

    @staticmethod
    def _has_attachments(db: Session, message_id: UUID) -> bool:
        return (
            db.query(AttachmentModel.id)
            .filter(AttachmentModel.message_id == message_id)
            .first()
            is not None
        )

    def _conversation_context_text(
        self,
        db: Session,
        message: MessageModel,
        architecture_mode: str,
    ) -> str:
        models = (
            db.query(MessageModel)
            .filter(MessageModel.conversation_id == message.conversation_id)
            .order_by(MessageModel.created_at_server.desc(), MessageModel.id.desc())
            .limit(self._settings.runtime_history_window_messages * 4)
            .all()
        )
        selected = [
            model
            for model in reversed(models)
            if self._belongs_to_runtime_history(model, architecture_mode)
        ][-self._settings.runtime_history_window_messages:]

        lines: list[str] = []
        for model in selected:
            text = (model.content_text or "").strip()
            if not text:
                continue
            role = {
                MessageDirection.INBOUND.value: "Usuario",
                MessageDirection.OUTBOUND.value: "Assistente",
                "system": "Sistema",
            }.get(model.direction, model.direction)
            lines.append(f"{role}: {text}")
        return "\n".join(lines) or (message.content_text or "")

    def _contextual_query_text(
        self,
        db: Session,
        message: MessageModel,
        architecture_mode: str,
    ) -> str:
        context = self._conversation_context_text(db, message, architecture_mode)
        latest = message.content_text or ""
        if not context:
            return latest
        return f"Ultima mensagem do usuario: {latest}\n\nContexto recente:\n{context}"

    def _belongs_to_runtime_history(
        self,
        message: MessageModel,
        architecture_mode: str,
    ) -> bool:
        if message.direction in {MessageDirection.INBOUND.value, "system"}:
            return True
        if message.direction != MessageDirection.OUTBOUND.value:
            return False

        message_architecture = (message.metadata_json or {}).get("architectureMode")
        if message_architecture:
            return message_architecture == architecture_mode

        return architecture_mode in {
            self._settings.default_architecture_mode,
            ArchitectureMode.CENTRALIZED_ORCHESTRATION.value,
        }

    def _event_context(self, message: MessageModel, architecture_mode: str) -> dict:
        metadata = message.metadata_json or {}
        return {
            "architectureMode": architecture_mode,
            "requestId": metadata.get("requestId"),
            "runtimeMode": metadata.get("runtimeMode", self._settings.runtime_mode),
        }

    def _base_payload(self, payload: dict, event_context: dict | None = None) -> dict:
        return {
            "architectureMode": self._settings.default_architecture_mode,
            "runtimeMode": self._settings.runtime_mode,
            **(event_context or {}),
            **payload,
        }

    # ------------------------------------------------------------------
    # Mock metrics helpers
    # ------------------------------------------------------------------

    _TOOL_FOR_ROUTE: dict[str, str] = {
        "stock_lookup": "stock_lookup",
        "image_intake": "attachment_intake",
        "faq": "faq_lookup",
    }

    _TOOL_COUNTS: dict[str, int] = {
        "centralized_orchestration": 2,
        "structured_workflow": 4,
        "decentralized_swarm": 3,
    }

    _TOKEN_RANGES: dict[str, tuple[int, int, int, int]] = {
        "centralized_orchestration": (1800, 2600, 250, 450),
        "structured_workflow": (1400, 2200, 200, 380),
        "decentralized_swarm": (2400, 3600, 320, 560),
    }

    def _simulate_tool_call(
        self,
        run_execution: RunExecutionService,
        *,
        run_id: UUID,
        conversation_id: UUID,
        message_id: UUID,
        correlation_id: UUID,
        actor_name: str,
        node_id: str,
        route: str,
        event_context: dict,
        count: int = 1,
        suppress_public_events: bool = False,
    ) -> None:
        tool_name = self._TOOL_FOR_ROUTE.get(route, "faq_lookup")
        for _ in range(count):
            self._record_run_event(
                run_execution,
                run_id=run_id,
                conversation_id=conversation_id,
                message_id=message_id,
                correlation_id=correlation_id,
                event_family="tool",
                event_name="started",
                status=ProcessingStatus.RUNNING,
                actor_name=actor_name,
                node_id=node_id,
                payload=self._base_payload({"toolName": tool_name, "input": {"query": "mock"}}, event_context),
                suppress_public_events=suppress_public_events,
            )
            self._record_run_event(
                run_execution,
                run_id=run_id,
                conversation_id=conversation_id,
                message_id=message_id,
                correlation_id=correlation_id,
                event_family="tool",
                event_name="completed",
                status=ProcessingStatus.COMPLETED,
                actor_name=actor_name,
                node_id=node_id,
                payload=self._base_payload({"toolName": tool_name, "result": {"status": "ok"}}, event_context),
                suppress_public_events=suppress_public_events,
            )

    def _mock_token_usage(self, architecture_mode: str) -> dict[str, int]:
        in_lo, in_hi, out_lo, out_hi = self._TOKEN_RANGES.get(
            architecture_mode, (1800, 2600, 250, 450)
        )
        input_tokens = random.randint(in_lo, in_hi)
        output_tokens = random.randint(out_lo, out_hi)
        return {"inputTokens": input_tokens, "outputTokens": output_tokens, "totalTokens": input_tokens + output_tokens}


def _normalize_text(text: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def _infer_product_name(text: str | None) -> str | None:
    normalized = _normalize_text(text)
    matches = [
        (normalized.index(product), product)
        for product in STOCK_CATALOG
        if product in normalized
    ]
    return min(matches)[1] if matches else None


def _looks_like_stock_question_text(text: str | None) -> bool:
    normalized = _normalize_text(text)
    return any(term in normalized for term in STOCK_TERMS)


def _looks_like_opening_hours_question(text: str | None) -> bool:
    normalized = _normalize_text(text)
    return any(
        term in normalized
        for term in ["horario", "funcionamento", "abre", "abrem", "abertura", "fecha", "fechamento"]
    )
