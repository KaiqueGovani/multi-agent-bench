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


# ===========================================================================
# Centralized-specific tests
# ===========================================================================

def test_centralized_zero_loop_count(monkeypatch) -> None:
    """Centralized mock never increments loop_count."""
    _patch_callbacks(monkeypatch)
    result = RuntimeExecutionService().execute_run(
        _build_request("centralized_orchestration", "Qual o horario?")
    )
    assert result.loop_count == 0


def test_centralized_zero_handoffs(monkeypatch) -> None:
    """Centralized mock emits no handoff events and handoff_count == 0."""
    full_events = _patch_callbacks_full(monkeypatch)
    result = RuntimeExecutionService().execute_run(
        _build_request("centralized_orchestration", "Qual o horario?")
    )
    handoff_events = [e for e in full_events if e.event_family == "handoff"]
    assert len(handoff_events) == 0
    assert result.handoff_count == 0


def test_centralized_single_reasoning(monkeypatch) -> None:
    """Centralized mock emits exactly one actor.reasoning event."""
    full_events = _patch_callbacks_full(monkeypatch)
    RuntimeExecutionService().execute_run(
        _build_request("centralized_orchestration", "Qual o horario?")
    )
    reasoning = [e for e in full_events if e.event_family == "actor" and e.event_name == "reasoning"]
    assert len(reasoning) == 1


def test_centralized_supervisor_is_final_actor(monkeypatch) -> None:
    """The response.final event must have actor_name == 'supervisor_agent'."""
    full_events = _patch_callbacks_full(monkeypatch)
    RuntimeExecutionService().execute_run(
        _build_request("centralized_orchestration", "Qual o horario?")
    )
    final_events = [e for e in full_events if e.event_family == "response" and e.event_name == "final"]
    assert len(final_events) == 1
    assert final_events[0].actor_name == "supervisor_agent"


# ===========================================================================
# Workflow-specific tests
# ===========================================================================

def test_workflow_loop_count_at_least_4(monkeypatch) -> None:
    """Workflow mock runs >= 4 stages (classify + evidence + review + synthesize)."""
    _patch_callbacks(monkeypatch)
    result = RuntimeExecutionService().execute_run(
        _build_request("structured_workflow", "Qual o horario?")
    )
    assert result.loop_count >= 4


def test_workflow_multiple_reasoning_events(monkeypatch) -> None:
    """Workflow mock emits >= 3 actor.reasoning events (one per stage)."""
    full_events = _patch_callbacks_full(monkeypatch)
    RuntimeExecutionService().execute_run(
        _build_request("structured_workflow", "Qual o horario?")
    )
    reasoning = [e for e in full_events if e.event_family == "actor" and e.event_name == "reasoning"]
    assert len(reasoning) >= 3


def test_workflow_node_started_completed_pairs(monkeypatch) -> None:
    """Every node.started must have a matching node.completed."""
    full_events = _patch_callbacks_full(monkeypatch)
    RuntimeExecutionService().execute_run(
        _build_request("structured_workflow", "Qual o horario?")
    )
    started = [e for e in full_events if e.event_family == "node" and e.event_name == "started"]
    completed = [e for e in full_events if e.event_family == "node" and e.event_name == "completed"]
    # Count by actor_name — every started actor must have a completed counterpart
    started_actors = sorted(e.actor_name for e in started)
    completed_actors = sorted(e.actor_name for e in completed)
    assert started_actors == completed_actors


def test_workflow_router_agent_first_reasoning(monkeypatch) -> None:
    """The first actor.reasoning event must come from router_agent."""
    full_events = _patch_callbacks_full(monkeypatch)
    RuntimeExecutionService().execute_run(
        _build_request("structured_workflow", "Qual o horario?")
    )
    reasoning = [e for e in full_events if e.event_family == "actor" and e.event_name == "reasoning"]
    assert len(reasoning) >= 1
    assert reasoning[0].actor_name == "router_agent"


def test_workflow_zero_handoffs(monkeypatch) -> None:
    """Workflow mock emits no handoff.requested events and handoff_count == 0."""
    full_events = _patch_callbacks_full(monkeypatch)
    result = RuntimeExecutionService().execute_run(
        _build_request("structured_workflow", "Qual o horario?")
    )
    handoff_requested = [
        e for e in full_events
        if e.event_family == "handoff" and e.event_name == "requested"
    ]
    assert len(handoff_requested) == 0
    assert result.handoff_count == 0


def test_workflow_multimodal_stage_with_attachments(monkeypatch) -> None:
    """Workflow mock with attachments emits an image_intake_agent multimodal node."""
    full_events = _patch_callbacks_full(monkeypatch)
    attachment = _make_attachment()
    RuntimeExecutionService().execute_run(
        _build_request("structured_workflow", "Analise esta foto", attachments=[attachment])
    )
    multimodal = [
        e for e in full_events
        if e.actor_name == "image_intake_agent" and e.node_id and "multimodal" in e.node_id
    ]
    assert len(multimodal) > 0


# ===========================================================================
# Swarm-specific tests
# ===========================================================================

def test_swarm_handoff_events_emitted(monkeypatch) -> None:
    """Swarm mock emits at least 2 handoff.requested events."""
    full_events = _patch_callbacks_full(monkeypatch)
    RuntimeExecutionService().execute_run(
        _build_request("decentralized_swarm", "Qual o horario?")
    )
    handoff_requested = [
        e for e in full_events
        if e.event_family == "handoff" and e.event_name == "requested"
    ]
    assert len(handoff_requested) >= 2


def test_swarm_multiple_reasoning_events(monkeypatch) -> None:
    """Swarm mock emits at least 2 actor.reasoning events (one per node)."""
    full_events = _patch_callbacks_full(monkeypatch)
    RuntimeExecutionService().execute_run(
        _build_request("decentralized_swarm", "Qual o horario?")
    )
    reasoning = [e for e in full_events if e.event_family == "actor" and e.event_name == "reasoning"]
    assert len(reasoning) >= 2


def test_swarm_coordinator_first_reasoning(monkeypatch) -> None:
    """The first actor.reasoning event must come from swarm_coordinator."""
    full_events = _patch_callbacks_full(monkeypatch)
    RuntimeExecutionService().execute_run(
        _build_request("decentralized_swarm", "Qual o horario?")
    )
    reasoning = [e for e in full_events if e.event_family == "actor" and e.event_name == "reasoning"]
    assert len(reasoning) >= 1
    assert reasoning[0].actor_name == "swarm_coordinator"


def test_swarm_handoff_count_in_result(monkeypatch) -> None:
    """ExecutionResult.handoff_count >= 2 and matches emitted handoff.requested count."""
    full_events = _patch_callbacks_full(monkeypatch)
    result = RuntimeExecutionService().execute_run(
        _build_request("decentralized_swarm", "Qual o horario?")
    )
    handoff_requested = [
        e for e in full_events
        if e.event_family == "handoff" and e.event_name == "requested"
    ]
    assert result.handoff_count >= 2
    assert result.handoff_count == len(handoff_requested)


def test_swarm_loop_count_matches_handoff_count(monkeypatch) -> None:
    """In mock mode, loop_count is incremented alongside handoff_count; both >= 2."""
    _patch_callbacks(monkeypatch)
    result = RuntimeExecutionService().execute_run(
        _build_request("decentralized_swarm", "Qual o horario?")
    )
    assert result.loop_count >= 2


# ===========================================================================
# Max handoffs guardrail test — tests _make_handoff_tool closure directly
# ===========================================================================

def test_swarm_max_handoffs_guardrail() -> None:
    """The handoff_to_peer closure must block after runtime_max_handoffs calls."""
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from app.architectures import swarm

    ctx = SimpleNamespace(
        settings=SimpleNamespace(runtime_max_handoffs=3),
        handoff_count=0,
        loop_count=0,
        emit=MagicMock(),
        emit_message=MagicMock(),
    )
    mock_peer = MagicMock(return_value="ok")
    agents = {"faq_specialist": mock_peer}
    handoff_count_ref = [0]

    handoff_fn = swarm._make_handoff_tool(ctx, agents, handoff_count_ref, original_text="test")

    # First 3 calls succeed
    for i in range(3):
        result = handoff_fn(peer_name="faq_specialist", reason="test")
        assert "peer" in result and result["peer"] == "faq_specialist"

    # 4th call must be blocked
    result = handoff_fn(peer_name="faq_specialist", reason="test")
    assert result["error"] == "max_handoffs_exceeded"


# ===========================================================================
# Handoff count field propagation in RunSummary
# ===========================================================================

def test_handoff_count_field_in_run_summary() -> None:
    """RunSummary correctly stores handoff_count."""
    from app.schemas.runtime import RunSummary

    summary = RunSummary(handoff_count=2, loop_count=3)
    assert summary.handoff_count == 2


# ===========================================================================
# Unknown architecture mode — graceful failure
# ===========================================================================

def test_unknown_architecture_mode_fails_gracefully(monkeypatch) -> None:
    emitted = _patch_callbacks(monkeypatch)
    result = RuntimeExecutionService().execute_run(_build_request("nonexistent_arch", "Ola"))
    assert result.final_outcome == "failed"
    assert result.human_review_required is False
    assert any(e == ("complete", "completed") for e in emitted)


# ===========================================================================
# Handoff tool peer exception handling
# ===========================================================================

def test_swarm_handoff_tool_handles_peer_exception() -> None:
    """handoff_to_peer returns error dict when peer agent raises."""
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from app.architectures import swarm

    ctx = SimpleNamespace(
        settings=SimpleNamespace(runtime_max_handoffs=6),
        handoff_count=0,
        loop_count=0,
        tool_error_count=0,
        emit=MagicMock(),
        emit_message=MagicMock(),
    )
    boom_peer = MagicMock(side_effect=RuntimeError("boom"))
    agents = {"exploder": boom_peer}
    handoff_count_ref = [0]

    handoff_fn = swarm._make_handoff_tool(ctx, agents, handoff_count_ref, original_text="test")
    result = handoff_fn(peer_name="exploder", reason="test")

    assert result["error"] == "peer_failed"
    assert result["peer"] == "exploder"
    assert "boom" in result["message"]
    assert ctx.tool_error_count == 1

    # Verify node.completed with status="failed" was emitted
    node_completed_calls = [
        c for c in ctx.emit.call_args_list
        if c[0][:3] == ("node", "completed", "failed")
    ]
    assert len(node_completed_calls) == 1