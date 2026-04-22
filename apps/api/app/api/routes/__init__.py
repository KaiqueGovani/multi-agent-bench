from fastapi import APIRouter

from app.api.routes import attachments, conversations, events, health, messages

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(messages.router, prefix="/messages", tags=["messages"])
api_router.include_router(events.router, tags=["events"])
api_router.include_router(attachments.router, prefix="/attachments", tags=["attachments"])

