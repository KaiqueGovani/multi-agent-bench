from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.db.models import MessageModel
from app.schemas.whatsapp import WhatsAppImportRequest, WhatsAppImportResponse
from app.services.processing_dispatcher import ProcessingDispatcher
from app.services.whatsapp_import import (
    WhatsAppImportConflict, WhatsAppImportService, WhatsAppRuntimeUnavailable,
)

router = APIRouter()


@router.post("/integrations/whatsapp/import", response_model=WhatsAppImportResponse, status_code=202)
async def import_whatsapp_conversation(
    request: WhatsAppImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
) -> WhatsAppImportResponse:
    try:
        result = await WhatsAppImportService(db).import_capture(request)
    except WhatsAppImportConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except WhatsAppRuntimeUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not result.reused:
        target = db.get(MessageModel, result.message_id)
        dispatches = [dict(conversation_id=result.conversation_id, message_id=result.message_id,
                           correlation_id=target.correlation_id, run_id=run_id)
                      for run_id in result.run_ids]
        background_tasks.add_task(ProcessingDispatcher().dispatch_many, dispatches=dispatches)
    return result
