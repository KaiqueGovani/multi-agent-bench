import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AttachmentModel, MessageModel
from app.db.session import SessionLocal
from app.schemas.enums import (
    MessageDirection,
    MessageStatus,
    ProcessingEventType,
    ProcessingStatus,
)
from app.services.events import EventService


class MockProcessingRuntime:
    def __init__(self, step_delay_seconds: float = 0.35) -> None:
        self._step_delay_seconds = step_delay_seconds
        self._settings = get_settings()

    def process_message(
        self,
        *,
        conversation_id: UUID,
        message_id: UUID,
        correlation_id: UUID,
    ) -> None:
        with SessionLocal() as db:
            message = db.get(MessageModel, message_id)
            if message is None:
                return

            message.status = MessageStatus.PROCESSING.value
            db.commit()

            event_service = EventService(db)
            started_at = datetime.now(UTC)
            event_context = self._event_context(message)
            self._record(
                event_service,
                conversation_id=conversation_id,
                message_id=message_id,
                correlation_id=correlation_id,
                event_type=ProcessingEventType.PROCESSING_STARTED,
                status=ProcessingStatus.RUNNING,
                payload=self._base_payload({"messageId": str(message_id)}, event_context),
            )

            self._invoke_actor(
                db,
                event_service,
                conversation_id=conversation_id,
                message_id=message_id,
                correlation_id=correlation_id,
                actor_name="router_agent",
                reason="classifying incoming request",
                result={"route": self._select_route(db, message)},
                event_context=event_context,
            )

            selected_actor = self._select_actor(db, message)
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
                result={"reviewRequired": False},
                event_context=event_context,
            )

            outbound_message = self._create_outbound_message(
                db,
                inbound_message=message,
                correlation_id=correlation_id,
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
                        "reviewRequired": False,
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
                "totalDurationMs": total_duration_ms,
            }
            message.status = MessageStatus.COMPLETED.value
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
        self._record(
            event_service,
            conversation_id=conversation_id,
            message_id=message_id,
            correlation_id=correlation_id,
            event_type=ProcessingEventType.ACTOR_INVOKED,
            actor_name=actor_name,
            status=ProcessingStatus.RUNNING,
            payload=self._base_payload({"reason": reason}, event_context),
        )
        time.sleep(self._step_delay_seconds)
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
        duration_ms: int | None = None,
    ) -> None:
        event_service.record_event(
            conversation_id=conversation_id,
            message_id=message_id,
            event_type=event_type,
            actor_name=actor_name,
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
    ) -> MessageModel:
        outbound = MessageModel(
            id=uuid4(),
            conversation_id=inbound_message.conversation_id,
            direction=MessageDirection.OUTBOUND.value,
            content_text=(
                "Recebi sua solicitacao. Esta e uma resposta simulada da POC; "
                "nenhum agente real ou decisao farmaceutica foi executado."
            ),
            created_at_server=datetime.now(UTC),
            status=MessageStatus.COMPLETED.value,
            correlation_id=correlation_id,
            metadata_json={
                "channel": self._settings.default_channel,
                "architectureMode": self._settings.default_architecture_mode,
                "runtimeMode": self._settings.runtime_mode,
                "reviewRequired": False,
            },
            model_context_json={
                "language": "pt-BR",
                "inferredIntent": self._infer_intent(inbound_message.content_text),
            },
        )
        db.add(outbound)
        db.commit()
        db.refresh(outbound)
        return outbound

    def _select_route(self, db: Session, message: MessageModel) -> str:
        if self._has_attachments(db, message.id):
            return "image_intake"
        if self._looks_like_stock_question(message.content_text):
            return "stock_lookup"
        return "faq"

    def _select_actor(self, db: Session, message: MessageModel) -> str:
        route = self._select_route(db, message)
        if route == "image_intake":
            return "image_intake_agent"
        if route == "stock_lookup":
            return "stock_agent"
        return "faq_agent"

    def _infer_intent(self, text: str | None) -> str:
        if self._looks_like_stock_question(text):
            return "stock_availability"
        return "general_question"

    @staticmethod
    def _looks_like_stock_question(text: str | None) -> bool:
        normalized = (text or "").lower()
        return any(term in normalized for term in ["tem ", "estoque", "disponivel", "disponível"])

    @staticmethod
    def _has_attachments(db: Session, message_id: UUID) -> bool:
        return (
            db.query(AttachmentModel.id)
            .filter(AttachmentModel.message_id == message_id)
            .first()
            is not None
        )

    def _event_context(self, message: MessageModel) -> dict:
        metadata = message.metadata_json or {}
        return {
            "architectureMode": metadata.get(
                "architectureMode",
                self._settings.default_architecture_mode,
            ),
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
