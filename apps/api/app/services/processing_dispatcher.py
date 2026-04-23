from __future__ import annotations

import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from app.core.config import get_settings
from app.core.tracing import build_baggage, build_traceparent
from app.db.models import MessageModel, RunModel
from app.db.session import SessionLocal
from app.runtime.mock import MockProcessingRuntime
from app.schemas.domain import RunSummary
from app.schemas.enums import MessageStatus, ProcessingEventType, ProcessingStatus, RunStatus
from app.services.events import EventService
from app.services.runs import RunService


class ProcessingDispatcher:
    def __init__(self) -> None:
        self._settings = get_settings()

    def dispatch(
        self,
        *,
        conversation_id: UUID,
        message_id: UUID,
        correlation_id: UUID,
        run_id: UUID,
    ) -> None:
        if self._settings.runtime_mode == "real" and self._settings.ai_runtime_url:
            self._dispatch_external(
                conversation_id=conversation_id,
                message_id=message_id,
                correlation_id=correlation_id,
                run_id=run_id,
            )
            return

        self._dispatch_mock(
            conversation_id=conversation_id,
            message_id=message_id,
            correlation_id=correlation_id,
            run_id=run_id,
        )

    def _dispatch_mock(
        self,
        *,
        conversation_id: UUID,
        message_id: UUID,
        correlation_id: UUID,
        run_id: UUID,
    ) -> None:
        started_at = time.perf_counter()
        with SessionLocal() as db:
            RunService(db).mark_running(run_id)

        MockProcessingRuntime().process_message(
            conversation_id=conversation_id,
            message_id=message_id,
            correlation_id=correlation_id,
        )

        duration_ms = int((time.perf_counter() - started_at) * 1000)
        with SessionLocal() as db:
            message = db.get(MessageModel, message_id)
            human_review_required = (
                message is not None
                and message.status == MessageStatus.HUMAN_REVIEW_REQUIRED.value
            )
            RunService(db).complete_run(
                run_id,
                status=(
                    RunStatus.HUMAN_REVIEW_REQUIRED
                    if human_review_required
                    else RunStatus.COMPLETED
                ),
                total_duration_ms=duration_ms,
                human_review_required=human_review_required,
                final_outcome=(
                    "human_review_required"
                    if human_review_required
                    else "answered"
                ),
                summary=RunSummary(
                    final_outcome=(
                        "human_review_required"
                        if human_review_required
                        else "answered"
                    )
                ),
            )

    def _dispatch_external(
        self,
        *,
        conversation_id: UUID,
        message_id: UUID,
        correlation_id: UUID,
        run_id: UUID,
    ) -> None:
        with SessionLocal() as db:
            run = RunService(db).mark_running(run_id)
            if run is None:
                return
            run_model = db.get(RunModel, run_id)
            traceparent = (
                build_traceparent(run_model.trace_id)
                if run_model and run_model.trace_id
                else None
            )
            payload = {
                "conversationId": str(conversation_id),
                "messageId": str(message_id),
                "runId": str(run_id),
                "correlationId": str(correlation_id),
                "aiSessionId": run_model.ai_session_id if run_model else None,
                "architectureKey": (
                    run_model.experiment_json.get("architectureKey")
                    if run_model
                    else None
                ),
                "modelKey": (
                    run_model.experiment_json.get("modelName")
                    if run_model
                    else None
                ),
                "traceparent": traceparent,
            }
            headers = {
                "Content-Type": "application/json",
            }
            if run_model and traceparent:
                headers["traceparent"] = traceparent
                headers["baggage"] = build_baggage(
                    conversation_id=conversation_id,
                    message_id=message_id,
                    run_id=run_id,
                    architecture_key=run_model.experiment_json.get("architectureKey"),
                    model_key=run_model.experiment_json.get("modelName"),
                    experiment_id=run_model.experiment_json.get("experimentId"),
                )

        request = Request(
            self._settings.ai_runtime_url.rstrip("/") + "/runs",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers=headers,
        )
        try:
            with urlopen(request, timeout=self._settings.ai_runtime_timeout_seconds) as response:
                if response.status >= 400:
                    raise RuntimeError(f"AI runtime returned HTTP {response.status}")
        except (HTTPError, URLError, OSError, RuntimeError) as exc:
            with SessionLocal() as db:
                RunService(db).fail_run(run_id, reason=str(exc))
                EventService(db).record_event(
                    conversation_id=conversation_id,
                    message_id=message_id,
                    event_type=ProcessingEventType.ACTOR_FAILED,
                    actor_name="ai_runtime",
                    correlation_id=correlation_id,
                    status=ProcessingStatus.FAILED,
                    payload={
                        "runId": str(run_id),
                        "reason": str(exc),
                        "source": "chat_api",
                    },
                )
