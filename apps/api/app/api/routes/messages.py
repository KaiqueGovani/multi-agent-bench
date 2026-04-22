import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.schemas.api import SendMessageResponse
from app.schemas.domain import OperationalMetadata
from app.services import IncomingAttachment, MessageService, MessageValidationError

router = APIRouter()


@router.post("", response_model=SendMessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def send_message(
    conversation_id: Annotated[UUID, Form(alias="conversationId")],
    text: Annotated[str | None, Form()] = None,
    metadata_json: Annotated[str, Form()] = "{}",
    client_message_id: Annotated[str | None, Form(alias="clientMessageId")] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
    db: Session = Depends(get_db_session),
) -> SendMessageResponse:
    metadata = _parse_metadata(metadata_json, client_message_id)
    incoming_attachments = [
        IncomingAttachment(
            filename=file.filename or "attachment",
            content_type=file.content_type or "application/octet-stream",
            content=await file.read(),
        )
        for file in (files or [])
    ]

    try:
        return MessageService(db).create_message(
            conversation_id=conversation_id,
            text=text,
            metadata=metadata,
            attachments=incoming_attachments,
        )
    except MessageValidationError as exc:
        if str(exc) == "Conversation not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


def _parse_metadata(metadata_json: str, client_message_id: str | None) -> OperationalMetadata:
    try:
        raw_metadata = json.loads(metadata_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="metadata_json must be valid JSON",
        ) from exc

    if not isinstance(raw_metadata, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="metadata_json must be a JSON object",
        )

    if client_message_id:
        raw_metadata["clientMessageId"] = client_message_id

    try:
        return OperationalMetadata.model_validate(raw_metadata)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc
