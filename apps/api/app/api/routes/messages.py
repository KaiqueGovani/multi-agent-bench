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
from app.schemas.api import SendMessageResponse
from app.schemas.domain import OperationalMetadata, RunExperimentMetadata
from app.services import MessageService, MessageValidationError
from app.services.processing_dispatcher import ProcessingDispatcher
from app.services.runs import RunService

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
        run = RunService(db).create_run(
            conversation_id=response.conversation_id,
            message_id=response.message_id,
            correlation_id=response.correlation_id,
            ai_session_id=_build_ai_session_id(
                conversation_id=response.conversation_id,
                architecture_key=metadata.architecture_mode,
            ),
            trace_id=extract_trace_id(traceparent),
            experiment=_build_run_experiment(metadata),
        )
        background_tasks.add_task(
            ProcessingDispatcher().dispatch,
            conversation_id=response.conversation_id,
            message_id=response.message_id,
            correlation_id=response.correlation_id,
            run_id=run.id,
        )
        return response.model_copy(update={"run_id": run.id})
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


def _build_run_experiment(metadata: OperationalMetadata) -> RunExperimentMetadata:
    from app.core.config import get_settings

    settings = get_settings()
    extra = metadata.model_extra or {}
    return RunExperimentMetadata(
        architecture_family=extra.get("architectureFamily"),
        architecture_key=metadata.architecture_mode or settings.default_architecture_mode,
        architecture_version=extra.get("architectureVersion")
        or settings.default_architecture_version,
        routing_strategy=extra.get("routingStrategy"),
        memory_strategy=extra.get("memoryStrategy"),
        tool_executor_mode=extra.get("toolExecutorMode"),
        review_policy_version=extra.get("reviewPolicyVersion"),
        model_provider=extra.get("modelProvider") or settings.default_model_provider,
        model_name=extra.get("modelName") or settings.default_model_name,
        model_version=extra.get("modelVersion") or settings.default_model_version,
        prompt_bundle_version=extra.get("promptBundleVersion")
        or settings.default_prompt_bundle_version,
        toolset_version=extra.get("toolsetVersion") or settings.default_toolset_version,
        experiment_id=extra.get("experimentId") or settings.default_experiment_id,
        scenario_id=extra.get("scenarioId"),
        runtime_commit_sha=extra.get("runtimeCommitSha"),
    )


def _build_ai_session_id(
    *,
    conversation_id: UUID,
    architecture_key: str | None,
) -> str:
    from app.core.config import get_settings

    settings = get_settings()
    return ":".join(
        [
            str(conversation_id),
            architecture_key or settings.default_architecture_mode,
            settings.default_model_name,
            settings.default_experiment_id,
        ]
    )


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
