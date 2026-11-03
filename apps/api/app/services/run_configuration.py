"""Shared run configuration for channel adapters and HTTP entrypoints."""
from uuid import UUID

from app.schemas.domain import OperationalMetadata, RunExperimentMetadata
from app.schemas.enums import ArchitectureMode, RuntimeMode


WHATSAPP_APPLICATION_PROTOCOL = "architectural-comparison-v4.4"


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
    whatsapp_application: bool = False,
) -> RunExperimentMetadata:
    from app.core.config import get_settings

    settings = get_settings()
    extra = metadata.model_extra or {}
    file_types = metadata.file_types if metadata.file_types else extra.get("fileTypes")
    scenario_id = extra.get("scenarioId") or _classify_scenario(text, file_types)
    comparison = {}
    if whatsapp_application and metadata.runtime_mode == RuntimeMode.REAL:
        comparison = {"comparisonProtocol": WHATSAPP_APPLICATION_PROTOCOL, "comparisonSourceProfile": "application"}
    elif "comparisonProtocol" in extra:
        comparison = {"comparisonProtocol": extra["comparisonProtocol"]}
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
            **comparison,
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
