from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.observability import get_request_id
from app.db import get_db_session
from app.schemas.api import (
    ConversationDetailResponse,
    CreateConversationRequest,
    CreateConversationResponse,
    MessageListResponse,
)
from app.services import ConversationService
from app.services.events import EventService
from app.services.messages import MessageService

router = APIRouter()


@router.post("", response_model=CreateConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    request: CreateConversationRequest,
    request_id: UUID = Depends(get_request_id),
    db: Session = Depends(get_db_session),
) -> CreateConversationResponse:
    service = ConversationService(db)
    conversation = service.create_conversation(
        request.model_copy(
            update={
                "metadata": request.metadata.model_copy(
                    update={"request_id": request_id}
                )
            }
        )
    )
    return CreateConversationResponse(
        conversation_id=conversation.id,
        status=conversation.status,
        channel=conversation.channel,
        created_at=conversation.created_at,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db_session),
) -> ConversationDetailResponse:
    service = ConversationService(db)
    conversation = service.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    events = EventService(db).list_conversation_events(conversation_id)
    message_service = MessageService(db)
    return ConversationDetailResponse(
        conversation=conversation,
        messages=message_service.list_conversation_messages(conversation_id),
        attachments=message_service.list_conversation_attachments(conversation_id),
        events=events,
        review_tasks=service.list_review_tasks(conversation_id),
    )


@router.get("/{conversation_id}/messages", response_model=MessageListResponse)
def get_conversation_messages(
    conversation_id: UUID,
    db: Session = Depends(get_db_session),
) -> MessageListResponse:
    service = ConversationService(db)
    conversation = service.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    message_service = MessageService(db)
    return MessageListResponse(
        conversation_id=conversation.id,
        messages=message_service.list_conversation_messages(conversation_id),
        attachments=message_service.list_conversation_attachments(conversation_id),
    )
