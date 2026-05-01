"""Architecture-specific unit tests — centralized, workflow, swarm.

Each architecture is tested through RuntimeExecutionService().execute_run()
with monkeypatched callbacks (same pattern as test_runtime_service.py).

In mock mode (ENABLE_LIVE_LLM=false), every architecture returns a fixed
response with route="faq", reviewRequired=False, and "[modo mock]" label.
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


def _patch_callbacks_full(monkeypatch):
    """Capture full event objects for payload inspection."""
    full_events: list = []

    def capture_emit(self, event):
        full_events.append(event)

    def capture_complete(self, **kwargs):
        pass

    monkeypatch.setattr("app.services.callbacks.ChatApiCallbacks.emit_run_event", capture_emit)
    monkeypatch.setattr("app.services.callbacks.ChatApiCallbacks.complete_run", capture_complete)
    return full_events


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ARCHITECTURES = ["centralized_orchestration", "structured_workflow", "decentralized_swarm"]

SAMPLE_MESSAGES = [
    "Qual o horario da farmacia?",
    "Tem dipirona disponivel?",
    "Qual a dosagem de dipirona?",
]


# ---------------------------------------------------------------------------
# Smoke tests — one per architecture: fixed mock response
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("arch", ARCHITECTURES)
@pytest.mark.parametrize("question", SAMPLE_MESSAGES)
def test_mock_returns_fixed_response(monkeypatch, arch, question) -> None:
    """Any message in mock mode → route=faq, reviewRequired=False, [modo mock] label."""
    full_events = _patch_callbacks_full(monkeypatch)
    result = RuntimeExecutionService().execute_run(_build_request(arch, question))

    assert result.final_outcome == "answered"
    assert result.human_review_required is False
    assert result.tool_call_count > 0

    final_events = [e for e in full_events if e.event_family == "response" and e.event_name == "final"]
    assert len(final_events) == 1
    payload = final_events[0].payload
    assert payload["route"] == "faq"
    assert payload["reviewRequired"] is False
    assert "[modo mock]" in payload["contentText"]
    assert "{'" not in payload["contentText"]


# ---------------------------------------------------------------------------
# Attachment scenario — still routes to faq in mock mode
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("arch", ARCHITECTURES)
def test_attachment_still_routes_faq_in_mock(monkeypatch, arch) -> None:
    full_events = _patch_callbacks_full(monkeypatch)
    attachment = _make_attachment()
    result = RuntimeExecutionService().execute_run(
        _build_request(arch, "Analise esta foto", attachments=[attachment])
    )
    assert result.final_outcome == "answered"
    assert result.tool_call_count > 0
    final_events = [e for e in full_events if e.event_family == "response" and e.event_name == "final"]
    assert final_events[0].payload["route"] == "faq"


# ---------------------------------------------------------------------------
# response.final payload must include enriched keys
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("arch", ARCHITECTURES)
def test_response_final_payload_has_enriched_keys(monkeypatch, arch) -> None:
    full_events = _patch_callbacks_full(monkeypatch)
    RuntimeExecutionService().execute_run(_build_request(arch, "Qual o horario da farmacia?"))
    final_events = [e for e in full_events if e.event_family == "response" and e.event_name == "final"]
    assert len(final_events) == 1
    payload = final_events[0].payload
    assert "route" in payload
    assert "finalActor" in payload
    assert "architectureMode" in payload
    assert "reviewRequired" in payload
    assert "contentText" in payload


# ---------------------------------------------------------------------------
# actor.reasoning event must be emitted
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("arch", ARCHITECTURES)
def test_actor_reasoning_event_emitted(monkeypatch, arch) -> None:
    emitted = _patch_callbacks(monkeypatch)
    RuntimeExecutionService().execute_run(_build_request(arch, "Qual o horario?"))
    assert any(e[0] == "actor" and e[1] == "reasoning" for e in emitted)


# ---------------------------------------------------------------------------
# contentText must contain [modo mock] and no dict repr
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("arch", ARCHITECTURES)
def test_content_text_is_mock_prose(monkeypatch, arch) -> None:
    full_events = _patch_callbacks_full(monkeypatch)
    RuntimeExecutionService().execute_run(_build_request(arch, "Qual o horario da farmacia?"))
    final_events = [e for e in full_events if e.event_family == "response" and e.event_name == "final"]
    content = final_events[0].payload["contentText"]
    assert "[modo mock]" in content
    assert "{'" not in content


# ---------------------------------------------------------------------------
# Workflow-specific: no multimodal stage without attachments
# ---------------------------------------------------------------------------

def test_workflow_no_multimodal_stage_without_attachments(monkeypatch) -> None:
    full_events = _patch_callbacks_full(monkeypatch)
    RuntimeExecutionService().execute_run(
        _build_request("structured_workflow", "Qual o horario?")
    )
    multimodal_events = [e for e in full_events if e.node_id and "multimodal" in e.node_id]
    assert len(multimodal_events) == 0


# ---------------------------------------------------------------------------
# Swarm-specific: loop_count > 0
# ---------------------------------------------------------------------------

def test_swarm_has_positive_loop_count(monkeypatch) -> None:
    _patch_callbacks(monkeypatch)
    result = RuntimeExecutionService().execute_run(
        _build_request("decentralized_swarm", "Qual o horario?")
    )
    assert result.loop_count > 0


# ---------------------------------------------------------------------------
# Swarm-specific: actor.message event emitted
# ---------------------------------------------------------------------------

def test_swarm_emits_actor_message(monkeypatch) -> None:
    emitted = _patch_callbacks(monkeypatch)
    RuntimeExecutionService().execute_run(
        _build_request("decentralized_swarm", "Qual o horario?")
    )
    assert any(e[0] == "actor" and e[1] == "message" for e in emitted)


# ---------------------------------------------------------------------------
# Unknown architecture mode — graceful failure
# ---------------------------------------------------------------------------

def test_unknown_architecture_mode_fails_gracefully(monkeypatch) -> None:
    emitted = _patch_callbacks(monkeypatch)
    result = RuntimeExecutionService().execute_run(_build_request("nonexistent_arch", "Ola"))
    assert result.final_outcome == "failed"
    assert result.human_review_required is False
    assert any(e == ("complete", "completed") for e in emitted)
