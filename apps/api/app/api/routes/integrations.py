from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import verify_ai_service_secret
from app.db import get_db_session
from app.db.models import MessageModel, RunModel
from app.schemas.api import IngestProcessingEventRequest, IngestRunExecutionEventRequest
from app.schemas.domain import ProcessingEvent, RunExecutionEvent
from app.services import ConversationService
from app.services.events import EventService
from app.services.run_execution import RunExecutionService

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

    event_message_id = request.message_id

    if request.run_id is not None:
        run = db.get(RunModel, request.run_id)
        if (
            run is None
            or run.conversation_id != request.conversation_id
            or (
                request.message_id is not None
                and run.message_id != request.message_id
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Run not found for conversation and message",
            )
        event_message_id = run.message_id

    if event_message_id is not None:
        message = db.get(MessageModel, event_message_id)
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
            run_id=request.run_id,
        )
        if existing_event is not None:
            return existing_event

    payload = {
        **request.payload,
        "source": request.source,
    }
    if request.external_event_id:
        payload["externalEventId"] = request.external_event_id
    if request.run_id:
        payload["runId"] = str(request.run_id)

    return event_service.record_event(
        conversation_id=request.conversation_id,
        message_id=event_message_id,
        event_type=request.event_type,
        actor_name=request.actor_name,
        parent_event_id=request.parent_event_id,
        correlation_id=request.correlation_id,
        status=request.status,
        payload=payload,
        duration_ms=request.duration_ms,
    )


@router.post(
    "/integrations/ai/run-events",
    response_model=RunExecutionEvent,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_ai_service_secret)],
)
def ingest_ai_run_event(
    request: IngestRunExecutionEventRequest,
    db: Session = Depends(get_db_session),
) -> RunExecutionEvent:
    conversation = ConversationService(db).get_conversation(request.conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    run = db.get(RunModel, request.run_id)
    if run is None or run.conversation_id != request.conversation_id or run.message_id != request.message_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found for conversation and message",
        )

    message = db.get(MessageModel, request.message_id)
    if message is None or message.conversation_id != request.conversation_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found for conversation",
        )

    return RunExecutionService(db).record_event(
        run_id=request.run_id,
        conversation_id=request.conversation_id,
        message_id=request.message_id,
        correlation_id=request.correlation_id,
        event_family=request.event_family,
        event_name=request.event_name,
        status=request.status,
        payload=request.payload,
        actor_name=request.actor_name,
        node_id=request.node_id,
        tool_name=request.tool_name,
        source=request.source,
        external_event_id=request.external_event_id,
        duration_ms=request.duration_ms,
    )
