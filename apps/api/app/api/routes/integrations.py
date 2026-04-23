from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import verify_ai_service_secret
from app.db import get_db_session
from app.db.models import MessageModel
from app.schemas.api import IngestProcessingEventRequest
from app.schemas.domain import ProcessingEvent
from app.services import ConversationService
from app.services.events import EventService

router = APIRouter()


@router.post(
    "/integrations/ai/events",
    response_model=ProcessingEvent,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_ai_service_secret)],
)
def ingest_ai_event(
    request: IngestProcessingEventRequest,
    db: Session = Depends(get_db_session),
) -> ProcessingEvent:
    conversation = ConversationService(db).get_conversation(request.conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    if request.message_id is not None:
        message = db.get(MessageModel, request.message_id)
        if message is None or message.conversation_id != request.conversation_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found for conversation",
            )

    event_service = EventService(db)
    if request.external_event_id:
        existing_event = event_service.get_external_event(
            conversation_id=request.conversation_id,
            external_event_id=request.external_event_id,
        )
        if existing_event is not None:
            return existing_event

    payload = {
        **request.payload,
        "source": request.source,
    }
    if request.external_event_id:
        payload["externalEventId"] = request.external_event_id

    return event_service.record_event(
        conversation_id=request.conversation_id,
        message_id=request.message_id,
        event_type=request.event_type,
        actor_name=request.actor_name,
        parent_event_id=request.parent_event_id,
        correlation_id=request.correlation_id,
        status=request.status,
        payload=payload,
        duration_ms=request.duration_ms,
    )
