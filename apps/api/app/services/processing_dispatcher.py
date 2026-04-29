from __future__ import annotations

import json
import time
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.tracing import build_baggage, build_traceparent
from app.db.models import AttachmentModel, MessageModel, RunModel
from app.db.session import SessionLocal
from app.runtime.mock import MockProcessingRuntime
from app.schemas.domain import (
    OperationalMetadata,
    RuntimeAttachmentDescriptor,
    RuntimeCallbackConfig,
    RuntimeDispatchRequest,
    RuntimeMessageSnapshot,
)
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
            message_model = db.get(MessageModel, message_id)
            if run_model is None or message_model is None:
                return
            traceparent = (
                build_traceparent(run_model.trace_id)
                if run_model and run_model.trace_id
                else None
            )
            baggage = (
                build_baggage(
                    conversation_id=conversation_id,
                    message_id=message_id,
                    run_id=run_id,
                    architecture_key=run_model.experiment_json.get("architectureKey"),
                    model_key=run_model.experiment_json.get("modelName"),
                    experiment_id=run_model.experiment_json.get("experimentId"),
                )
                if run_model
                else None
            )
            payload = self._build_runtime_dispatch_request(
                run_model=run_model,
                message_model=message_model,
                traceparent=traceparent,
                baggage=baggage,
            ).model_dump(by_alias=True, mode="json", exclude_none=True)
            headers = {
                "Content-Type": "application/json",
            }
            if run_model and traceparent:
                headers["traceparent"] = traceparent
            if baggage:
                headers["baggage"] = baggage

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

    def _build_runtime_dispatch_request(
        self,
        *,
        run_model: RunModel,
        message_model: MessageModel,
        traceparent: str | None,
        baggage: str | None,
    ) -> RuntimeDispatchRequest:
        return RuntimeDispatchRequest(
            run_id=run_model.id,
            conversation_id=run_model.conversation_id,
            message_id=run_model.message_id,
            correlation_id=run_model.correlation_id,
            ai_session_id=run_model.ai_session_id,
            traceparent=traceparent,
            baggage=baggage,
            architecture_mode=run_model.experiment_json.get("architectureKey", self._settings.default_architecture_mode),
            experiment=run_model.experiment_json,
            latest_message=self._message_snapshot(message_model),
            conversation_history=self._conversation_history(run_model.conversation_id),
            callback=RuntimeCallbackConfig(
                base_url=self._settings.app_base_url.rstrip("/"),
                api_key=self._settings.api_key,
                ai_service_secret=self._settings.ai_service_secret,
            ),
        )

    def _conversation_history(self, conversation_id: UUID) -> list[RuntimeMessageSnapshot]:
        with SessionLocal() as db:
            models = (
                db.query(MessageModel)
                .filter(MessageModel.conversation_id == conversation_id)
                .order_by(MessageModel.created_at_server.desc(), MessageModel.id.desc())
                .limit(self._settings.runtime_history_window_messages)
                .all()
            )
            ordered = list(reversed(models))
            return [self._message_snapshot(model, db=db) for model in ordered]

    def _message_snapshot(
        self,
        message_model: MessageModel,
        *,
        db: Session | None = None,
    ) -> RuntimeMessageSnapshot:
        owns_session = db is None
        session = db or SessionLocal()
        try:
            attachments = (
                session.query(AttachmentModel)
                .filter(AttachmentModel.message_id == message_model.id)
                .order_by(AttachmentModel.created_at, AttachmentModel.id)
                .all()
            )
            return RuntimeMessageSnapshot(
                id=message_model.id,
                direction=message_model.direction,
                content_text=message_model.content_text,
                created_at_server=message_model.created_at_server,
                status=message_model.status,
                correlation_id=message_model.correlation_id,
                metadata=OperationalMetadata.model_validate(message_model.metadata_json or {}),
                attachments=[self._attachment_descriptor(attachment) for attachment in attachments],
            )
        finally:
            if owns_session:
                session.close()

    def _attachment_descriptor(self, attachment: AttachmentModel) -> RuntimeAttachmentDescriptor:
        query = urlencode({"apiKey": self._settings.api_key}) if self._settings.api_key else ""
        suffix = f"?{query}" if query else ""
        return RuntimeAttachmentDescriptor(
            attachment_id=attachment.id,
            message_id=attachment.message_id,
            original_filename=attachment.original_filename,
            mime_type=attachment.mime_type,
            size_bytes=attachment.size_bytes,
            checksum=attachment.checksum,
            width=attachment.width,
            height=attachment.height,
            page_count=(attachment.metadata_json or {}).get("pageCount"),
            retrieval_url=(
                f"{self._settings.app_base_url.rstrip('/')}/attachments/{attachment.id}{suffix}"
            ),
            metadata=OperationalMetadata.model_validate(attachment.metadata_json or {}),
        )
