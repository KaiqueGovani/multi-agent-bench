import asyncio
from queue import Empty
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.db import get_db_session
from app.schemas.domain import ProcessingEvent
from app.services import ConversationService, event_bus
from app.services.events import EventService

router = APIRouter()


@router.get("/conversations/{conversation_id}/events", response_model=list[ProcessingEvent])
def get_conversation_events(
    conversation_id: UUID,
    db: Session = Depends(get_db_session),
) -> list[ProcessingEvent]:
    conversation = ConversationService(db).get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    events = EventService(db).list_conversation_events(conversation_id)
    return events


@router.get("/conversations/{conversation_id}/events/stream")
async def stream_conversation_events(
    conversation_id: UUID,
    request: Request,
    last_event_id: UUID | None = Query(default=None, alias="lastEventId"),
    db: Session = Depends(get_db_session),
) -> EventSourceResponse:
    conversation = ConversationService(db).get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    subscriber = event_bus.subscribe(conversation_id)
    event_service = EventService(db)
    replay_after_id = _resolve_last_event_id(request, last_event_id)

    async def event_generator():
        try:
            replay_events = (
                event_service.list_conversation_events_after(
                    conversation_id=conversation_id,
                    last_event_id=replay_after_id,
                )
                if replay_after_id
                else []
            )
            for event in replay_events:
                yield _to_sse_event(event)

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.to_thread(subscriber.queue.get, True, 15)
                except Empty:
                    yield {
                        "event": "heartbeat",
                        "data": "{}",
                        "retry": 2000,
                    }
                    continue

                yield _to_sse_event(event)
        finally:
            event_bus.unsubscribe(conversation_id, subscriber)

    return EventSourceResponse(event_generator())


def _resolve_last_event_id(request: Request, query_value: UUID | None) -> UUID | None:
    if query_value is not None:
        return query_value
    header_value = request.headers.get("last-event-id")
    if not header_value:
        return None
    try:
        return UUID(header_value)
    except ValueError:
        return None


def _to_sse_event(event: ProcessingEvent) -> dict[str, str | int]:
    return {
        "event": "processing.event",
        "id": str(event.id),
        "data": event.model_dump_json(by_alias=True),
        "retry": 2000,
    }
