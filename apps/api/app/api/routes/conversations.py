from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.api import (
    ConversationDetailResponse,
    CreateConversationRequest,
    CreateConversationResponse,
    MessageListResponse,
)
from app.services import ConversationService, get_conversation_service

router = APIRouter()


@router.post("", response_model=CreateConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    request: CreateConversationRequest,
    service: ConversationService = Depends(get_conversation_service),
) -> CreateConversationResponse:
    conversation = service.create_conversation(request)
    return CreateConversationResponse(
        conversation_id=conversation.id,
        status=conversation.status.value,
        channel=conversation.channel,
        created_at=conversation.created_at,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: UUID,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationDetailResponse:
    conversation = service.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return ConversationDetailResponse(conversation=conversation)


@router.get("/{conversation_id}/messages", response_model=MessageListResponse)
def get_conversation_messages(
    conversation_id: UUID,
    service: ConversationService = Depends(get_conversation_service),
) -> MessageListResponse:
    conversation = service.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return MessageListResponse(conversation_id=conversation.id)

