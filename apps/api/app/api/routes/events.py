from uuid import UUID

from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.get("/conversations/{conversation_id}/events/stream", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def stream_conversation_events(conversation_id: UUID) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="SSE event streaming will be implemented in execution step 7.",
    )

