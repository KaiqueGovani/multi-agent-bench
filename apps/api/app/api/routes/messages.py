import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.adapters.inbound import WebChatAdapter
from app.core.observability import get_request_id
from app.core.tracing import extract_trace_id
from app.db import get_db_session
from app.db.models import ConversationModel
from app.schemas.api import SendMessageResponse
from app.schemas.domain import OperationalMetadata, RunExperimentMetadata
from app.schemas.enums import ArchitectureMode
from app.services import MessageService, MessageValidationError
from app.services.processing_dispatcher import ProcessingDispatcher
from app.services.runs import RunService
from app.services.run_configuration import (
    _build_ai_session_id, _build_run_experiment, _expand_architecture_keys, _classify_scenario,
)

router = APIRouter()


@router.post("", response_model=SendMessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def send_message(
    background_tasks: BackgroundTasks,
    conversation_id: Annotated[UUID, Form(alias="conversationId")],
    text: Annotated[str | None, Form()] = None,
    metadata_json: Annotated[str, Form()] = "{}",
    client_message_id: Annotated[str | None, Form(alias="clientMessageId")] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
    traceparent: Annotated[str | None, Header()] = None,
    request_id: UUID = Depends(get_request_id),
    db: Session = Depends(get_db_session),
) -> SendMessageResponse:
    metadata = _parse_metadata(metadata_json, client_message_id).model_copy(
        update={"request_id": request_id}
    )
    inbound_message = await WebChatAdapter().normalize_inbound_message(
        conversation_id=conversation_id,
        text=text,
        metadata=metadata,
        client_message_id=client_message_id,
        files=files,
    )

    try:
        response = MessageService(db).create_message(
            inbound=inbound_message,
        )
        conversation = db.get(ConversationModel, response.conversation_id)
        whatsapp_application = (
            conversation is not None
            and conversation.channel == "whatsapp"
            and (conversation.metadata_json or {}).get("source") == "whatsapp_web"
        )
        architecture_keys = _expand_architecture_keys(metadata.architecture_mode)
        created_runs = []
        dispatches: list[dict[str, UUID]] = []
        for index, architecture_key in enumerate(architecture_keys):
            run = RunService(db).create_run(
                conversation_id=response.conversation_id,
                message_id=response.message_id,
                correlation_id=response.correlation_id,
                ai_session_id=_build_ai_session_id(
                    conversation_id=response.conversation_id,
                    architecture_key=architecture_key,
                ),
                trace_id=extract_trace_id(traceparent),
                experiment=_build_run_experiment(
                    metadata,
                    architecture_key=architecture_key,
                    comparison_only=len(architecture_keys) > 1 and index > 0,
                    text=text,
                    whatsapp_application=whatsapp_application,
                ),
            )
            dispatches.append(
                {
                    "conversation_id": response.conversation_id,
                    "message_id": response.message_id,
                    "correlation_id": response.correlation_id,
                    "run_id": run.id,
                }
            )
            created_runs.append(run)
        background_tasks.add_task(
            ProcessingDispatcher().dispatch_many,
            dispatches=dispatches,
        )
        return response.model_copy(update={"run_id": created_runs[0].id if created_runs else None})
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
