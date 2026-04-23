from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.db.mappers import processing_event_to_schema
from app.db.models import ProcessingEventModel
from app.schemas.domain import JsonObject, ProcessingEvent
from app.schemas.enums import ProcessingEventType, ProcessingStatus
from app.services.event_bus import InMemoryEventBus, event_bus


class EventService:
    def __init__(self, db: Session, bus: InMemoryEventBus = event_bus) -> None:
        self._db = db
        self._bus = bus

    def record_event(
        self,
        *,
        conversation_id: UUID,
        event_type: ProcessingEventType,
        correlation_id: UUID,
        status: ProcessingStatus,
        payload: JsonObject | None = None,
        message_id: UUID | None = None,
        actor_name: str | None = None,
        parent_event_id: UUID | None = None,
        duration_ms: int | None = None,
        commit: bool = True,
        publish: bool = True,
    ) -> ProcessingEvent:
        event_model = ProcessingEventModel(
            id=uuid4(),
            conversation_id=conversation_id,
            message_id=message_id,
            event_type=event_type.value,
            actor_name=actor_name,
            parent_event_id=parent_event_id,
            correlation_id=correlation_id,
            payload_json=payload or {},
            created_at=datetime.now(UTC),
            duration_ms=duration_ms,
            status=status.value,
        )
        self._db.add(event_model)
        if commit:
            self._db.commit()
        else:
            self._db.flush()
        self._db.refresh(event_model)
        event = processing_event_to_schema(event_model)
        if publish:
            self._bus.publish(event)
        return event

    def list_conversation_events(self, conversation_id: UUID) -> list[ProcessingEvent]:
        statement = (
            select(ProcessingEventModel)
            .where(ProcessingEventModel.conversation_id == conversation_id)
            .order_by(ProcessingEventModel.created_at, ProcessingEventModel.id)
        )
        return [
            processing_event_to_schema(event_model)
            for event_model in self._db.scalars(statement).all()
        ]

    def list_conversation_events_after(
        self,
        *,
        conversation_id: UUID,
        last_event_id: UUID,
    ) -> list[ProcessingEvent]:
        anchor = self._db.get(ProcessingEventModel, last_event_id)
        if anchor is None or anchor.conversation_id != conversation_id:
            return self.list_conversation_events(conversation_id)

        statement = (
            select(ProcessingEventModel)
            .where(
                ProcessingEventModel.conversation_id == conversation_id,
                or_(
                    ProcessingEventModel.created_at > anchor.created_at,
                    and_(
                        ProcessingEventModel.created_at == anchor.created_at,
                        ProcessingEventModel.id > anchor.id,
                    ),
                ),
            )
            .order_by(ProcessingEventModel.created_at, ProcessingEventModel.id)
        )
        return [
            processing_event_to_schema(event_model)
            for event_model in self._db.scalars(statement).all()
        ]

    def get_external_event(
        self,
        *,
        conversation_id: UUID,
        external_event_id: str,
        run_id: UUID | None = None,
    ) -> ProcessingEvent | None:
        for event in self.list_conversation_events(conversation_id):
            if event.payload.get("externalEventId") != external_event_id:
                continue
            if run_id is not None and event.payload.get("runId") != str(run_id):
                continue
            return event
        return None
