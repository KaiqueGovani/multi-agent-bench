from fastapi import APIRouter, Depends

from app.api.routes import attachments, conversations, events, health, integrations, messages
from app.core.security import verify_api_key

api_router = APIRouter()
api_router.include_router(health.router)
protected_dependencies = [Depends(verify_api_key)]
api_router.include_router(
    conversations.router,
    prefix="/conversations",
    tags=["conversations"],
    dependencies=protected_dependencies,
)
api_router.include_router(
    messages.router,
    prefix="/messages",
    tags=["messages"],
    dependencies=protected_dependencies,
)
api_router.include_router(events.router, tags=["events"], dependencies=protected_dependencies)
api_router.include_router(
    integrations.router,
    tags=["integrations"],
    dependencies=protected_dependencies,
)
api_router.include_router(
    attachments.router,
    prefix="/attachments",
    tags=["attachments"],
    dependencies=protected_dependencies,
)
