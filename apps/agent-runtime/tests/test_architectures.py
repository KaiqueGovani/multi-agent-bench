"""Architecture-specific unit tests — centralized, workflow, swarm.

Each architecture is tested through RuntimeExecutionService().execute_run()
with monkeypatched callbacks (same pattern as test_runtime_service.py).
"""

from uuid import uuid4

import pytest

from app.schemas.runtime import (
    OperationalMetadata,
    RunExperimentMetadata,
    RuntimeAttachmentDescriptor,
    RuntimeCallbackConfig,
    RuntimeDispatchRequest,
    RuntimeMessageSnapshot,
)
from app.services.execution import RuntimeExecutionService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_request(
    architecture_mode: str,
    content_text: str,
    attachments: list[RuntimeAttachmentDescriptor] | None = None,
) -> RuntimeDispatchRequest:
    correlation_id = uuid4()
    message = RuntimeMessageSnapshot(
        id=uuid4(),
        direction="inbound",
        content_text=content_text,
        created_at_server="2026-04-29T00:00:00Z",
        status="accepted",
        correlation_id=correlation_id,
        metadata=OperationalMetadata(architecture_mode=architecture_mode, runtime_mode="real"),
        attachments=attachments or [],
    )
    return RuntimeDispatchRequest(
        run_id=uuid4(),
        conversation_id=uuid4(),
        message_id=message.id,
        correlation_id=correlation_id,
        ai_session_id="session:test",
        architecture_mode=architecture_mode,
        experiment=RunExperimentMetadata(
            architecture_key=architecture_mode,
            model_name="test-model",
        ),
        latest_message=message,
        conversation_history=[message],
        callback=RuntimeCallbackConfig(base_url="http://127.0.0.1:8000"),
    )


def _make_attachment(mime_type: str = "image/png", filename: str = "foto.png") -> RuntimeAttachmentDescriptor:
    return RuntimeAttachmentDescriptor(
        attachment_id=uuid4(),
        message_id=uuid4(),
        original_filename=filename,
        mime_type=mime_type,
        size_bytes=128,
        checksum="abc123",
        width=32,
        height=32,
        retrieval_url="http://localhost/fake",
    )


def _patch_callbacks(monkeypatch):
    """Monkeypatch ChatApiCallbacks to capture events without HTTP calls."""
    emitted: list[tuple[str, str]] = []

    def fake_emit(self, event):
        emitted.append((event.event_family, event.event_name))

    def fake_complete(self, **kwargs):
        emitted.append(("complete", kwargs["status"]))

    monkeypatch.setattr("app.services.callbacks.ChatApiCallbacks.emit_run_event", fake_emit)
    monkeypatch.setattr("app.services.callbacks.ChatApiCallbacks.complete_run", fake_complete)
    return emitted


# ---------------------------------------------------------------------------
# Parametrized scenarios per architecture
# ---------------------------------------------------------------------------

ARCHITECTURES = ["centralized_orchestration", "structured_workflow", "decentralized_swarm"]

FAQ_SCENARIOS = [
    ("Qual o horario da farmacia?", "answered"),
    ("Como funciona a entrega?", "answered"),
    ("Qual a politica de devolucao?", "answered"),
]

STOCK_SCENARIOS = [
    ("Tem dipirona disponivel?", "answered"),
    ("Tem amoxicilina em estoque?", "answered"),
    ("Tem paracetamol?", "answered"),
]

REVIEW_SCENARIOS = [
    ("Preciso de revisao humana", "human_review_required"),
    ("Qual a dosagem correta?", "human_review_required"),
]


@pytest.mark.parametrize("arch", ARCHITECTURES)
@pytest.mark.parametrize("question,expected_outcome", FAQ_SCENARIOS)
def test_faq_scenario(monkeypatch, arch, question, expected_outcome) -> None:
    emitted = _patch_callbacks(monkeypatch)
    result = RuntimeExecutionService().execute_run(_build_request(arch, question))
    assert result.final_outcome == expected_outcome
    assert result.tool_call_count > 0
    assert any(e[0] == "response" and e[1] == "final" for e in emitted)


@pytest.mark.parametrize("arch", ARCHITECTURES)
@pytest.mark.parametrize("question,expected_outcome", STOCK_SCENARIOS)
def test_stock_scenario(monkeypatch, arch, question, expected_outcome) -> None:
    emitted = _patch_callbacks(monkeypatch)
    result = RuntimeExecutionService().execute_run(_build_request(arch, question))
    assert result.final_outcome == expected_outcome
    assert result.tool_call_count > 0
    assert any(e[0] == "response" and e[1] == "final" for e in emitted)


@pytest.mark.parametrize("arch", ARCHITECTURES)
@pytest.mark.parametrize("question,expected_outcome", REVIEW_SCENARIOS)
def test_review_scenario(monkeypatch, arch, question, expected_outcome) -> None:
    emitted = _patch_callbacks(monkeypatch)
    result = RuntimeExecutionService().execute_run(_build_request(arch, question))
    assert result.final_outcome == expected_outcome
    assert result.tool_call_count > 0
    assert any(e[0] == "review" and e[1] == "required" for e in emitted)


@pytest.mark.parametrize("arch", ARCHITECTURES)
def test_attachment_scenario(monkeypatch, arch) -> None:
    emitted = _patch_callbacks(monkeypatch)
    attachment = _make_attachment()
    result = RuntimeExecutionService().execute_run(
        _build_request(arch, "Analise esta foto", attachments=[attachment])
    )
    assert result.final_outcome == "answered"
    assert result.tool_call_count > 0
    assert any(e[0] == "response" and e[1] == "final" for e in emitted)


# ---------------------------------------------------------------------------
# Workflow-specific: multimodal stage only activates with attachments
# ---------------------------------------------------------------------------

def test_workflow_multimodal_stage_skipped_without_attachments(monkeypatch) -> None:
    full_events: list = []

    def capture_emit(self, event):
        full_events.append(event)

    def capture_complete(self, **kwargs):
        pass

    monkeypatch.setattr("app.services.callbacks.ChatApiCallbacks.emit_run_event", capture_emit)
    monkeypatch.setattr("app.services.callbacks.ChatApiCallbacks.complete_run", capture_complete)

    RuntimeExecutionService().execute_run(
        _build_request("structured_workflow", "Qual o horario?")
    )
    multimodal_events = [e for e in full_events if e.node_id and "multimodal" in e.node_id]
    assert len(multimodal_events) == 0


def test_workflow_multimodal_stage_activates_with_attachments(monkeypatch) -> None:
    full_events: list = []

    def capture_emit(self, event):
        full_events.append(event)

    def capture_complete(self, **kwargs):
        pass

    monkeypatch.setattr("app.services.callbacks.ChatApiCallbacks.emit_run_event", capture_emit)
    monkeypatch.setattr("app.services.callbacks.ChatApiCallbacks.complete_run", capture_complete)

    attachment = _make_attachment()
    RuntimeExecutionService().execute_run(
        _build_request("structured_workflow", "Analise esta foto", attachments=[attachment])
    )
    multimodal_events = [e for e in full_events if e.node_id and "multimodal" in e.node_id]
    assert len(multimodal_events) > 0


# ---------------------------------------------------------------------------
# Swarm-specific: loop_count > 0
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("question", ["Tem dipirona?", "Qual o horario?", "Analise a foto"])
def test_swarm_has_positive_loop_count(monkeypatch, question) -> None:
    _patch_callbacks(monkeypatch)
    attachments = [_make_attachment()] if "foto" in question else None
    result = RuntimeExecutionService().execute_run(
        _build_request("decentralized_swarm", question, attachments=attachments)
    )
    assert result.loop_count > 0


# ---------------------------------------------------------------------------
# Unknown architecture mode — graceful failure
# ---------------------------------------------------------------------------

def test_unknown_architecture_mode_fails_gracefully(monkeypatch) -> None:
    emitted = _patch_callbacks(monkeypatch)
    result = RuntimeExecutionService().execute_run(_build_request("nonexistent_arch", "Ola"))
    assert result.final_outcome == "failed"
    assert result.human_review_required is False
    assert any(e == ("complete", "completed") for e in emitted)