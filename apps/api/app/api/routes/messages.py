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
from app.schemas.enums import ArchitectureMode
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


def _classify_scenario(text: str | None, file_types: list[str] | None) -> str:
    """Classify the user message into a scenario based on content and attachments."""
    has_attachments = bool(file_types and len(file_types) > 0)
    has_image = has_attachments and any(
        ft.startswith("image/") for ft in (file_types or [])
    )
    has_pdf = has_attachments and any(
        ft == "application/pdf" for ft in (file_types or [])
    )

    if has_image or has_pdf:
        return "attachment_analysis"

    if not text:
        return "general_inquiry"

    lower = text.lower()

    clinical_keywords = [
        "dosagem", "dose", "tomar", "efeito colateral", "interação",
        "gestante", "grávida", "amamentar", "pressão", "diabetes",
        "alergia", "alérgico", "contraindicação", "posologia",
    ]
    if any(kw in lower for kw in clinical_keywords):
        return "clinical_guidance"

    stock_keywords = [
        "estoque", "disponível", "disponibilidade", "tem ", "têm ",
        "produto", "remédio", "medicamento", "preço", "quanto custa",
    ]
    if any(kw in lower for kw in stock_keywords):
        return "stock_inquiry"

    faq_keywords = [
        "horário", "entrega", "devolução", "pagamento", "troca",
        "funciona", "aberto", "aberta", "fecha", "delivery", "frete",
    ]
    if any(kw in lower for kw in faq_keywords):
        return "faq_inquiry"

    return "general_inquiry"


def _build_run_experiment(
    metadata: OperationalMetadata,
    *,
    architecture_key: str,
    comparison_only: bool,
    text: str | None = None,
) -> RunExperimentMetadata:
    from app.core.config import get_settings

    settings = get_settings()
    extra = metadata.model_extra or {}
    file_types = metadata.file_types if metadata.file_types else extra.get("fileTypes")
    scenario_id = extra.get("scenarioId") or _classify_scenario(text, file_types)
    return RunExperimentMetadata.model_validate(
        {
            "architectureFamily": extra.get("architectureFamily")
            or settings.default_architecture_family,
            "architectureKey": architecture_key,
            "architectureVersion": extra.get("architectureVersion")
            or settings.default_architecture_version,
            "routingStrategy": extra.get("routingStrategy")
            or settings.default_routing_strategy,
            "memoryStrategy": extra.get("memoryStrategy") or settings.default_memory_strategy,
            "toolExecutorMode": extra.get("toolExecutorMode")
            or settings.default_tool_executor_mode,
            "reviewPolicyVersion": extra.get("reviewPolicyVersion")
            or settings.default_review_policy_version,
            "modelProvider": extra.get("modelProvider") or settings.default_model_provider,
            "modelName": extra.get("modelName") or settings.default_model_name,
            "modelVersion": extra.get("modelVersion") or settings.default_model_version,
            "promptBundleVersion": extra.get("promptBundleVersion")
            or settings.default_prompt_bundle_version,
            "toolsetVersion": extra.get("toolsetVersion") or settings.default_toolset_version,
            "experimentId": extra.get("experimentId") or settings.default_experiment_id,
            "scenarioId": scenario_id,
            "runtimeCommitSha": extra.get("runtimeCommitSha"),
            "comparisonOnly": comparison_only,
            "requestedArchitectureMode": metadata.architecture_mode or architecture_key,
        }
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


def _expand_architecture_keys(requested_mode: str | None) -> list[str]:
    if requested_mode == ArchitectureMode.ALL_ARCHITECTURES.value:
        return [
            ArchitectureMode.CENTRALIZED_ORCHESTRATION.value,
            ArchitectureMode.STRUCTURED_WORKFLOW.value,
            ArchitectureMode.DECENTRALIZED_SWARM.value,
        ]
    return [requested_mode or ArchitectureMode.CENTRALIZED_ORCHESTRATION.value]


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
