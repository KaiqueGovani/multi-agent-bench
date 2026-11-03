from uuid import uuid4

import pytest

from app.schemas.runtime import (
    OperationalMetadata,
    RunExperimentMetadata,
    RuntimeCallbackConfig,
    RuntimeDispatchRequest,
    RuntimeMessageSnapshot,
)
from app.services.execution import RuntimeExecutionService, RuntimeExecutor
from app.core.config import Settings


def build_request(architecture_mode: str = "centralized_orchestration") -> RuntimeDispatchRequest:
    correlation_id = uuid4()
    message = RuntimeMessageSnapshot(
        id=uuid4(),
        direction="inbound",
        content_text="Tem dipirona em estoque?",
        created_at_server="2026-04-29T00:00:00Z",
        status="accepted",
        correlation_id=correlation_id,
        metadata=OperationalMetadata(architecture_mode=architecture_mode, runtime_mode="real"),
        attachments=[],
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
            model_name="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        ),
        latest_message=message,
        conversation_history=[message],
        callback=RuntimeCallbackConfig(base_url="http://127.0.0.1:8000"),
    )


def test_runtime_execution_service_returns_deterministic_result(monkeypatch) -> None:
    emitted: list[tuple[str, str]] = []

    def fake_emit(self, event):  # noqa: ANN001
        emitted.append((event.event_family, event.event_name))

    def fake_complete(self, **kwargs):  # noqa: ANN003, ANN001
        emitted.append(("complete", kwargs["status"]))

    monkeypatch.setattr("app.services.callbacks.ChatApiCallbacks.emit_run_event", fake_emit)
    monkeypatch.setattr("app.services.callbacks.ChatApiCallbacks.complete_run", fake_complete)

    result = RuntimeExecutionService().execute_run(build_request())
    assert result.final_outcome == "answered"
    assert any(item[0] == "response" and item[1] == "final" for item in emitted)


def test_runtime_execution_service_reports_failure_callback(monkeypatch) -> None:
    emitted: list[tuple[str, str]] = []

    def fake_execute(self):  # noqa: ANN001
        raise RuntimeError("boom")

    def fake_complete(self, **kwargs):  # noqa: ANN003, ANN001
        emitted.append((kwargs["status"], kwargs["final_outcome"]))

    monkeypatch.setattr(RuntimeExecutor, "execute", fake_execute)
    monkeypatch.setattr("app.services.callbacks.ChatApiCallbacks.complete_run", fake_complete)

    with pytest.raises(RuntimeError, match="boom"):
        RuntimeExecutionService().execute_run(build_request())

    assert emitted == [("failed", "runtime_failed")]


@pytest.mark.parametrize(
    "architecture",
    ["centralized_orchestration", "structured_workflow", "decentralized_swarm"],
)
def test_comparison_service_preserves_config_history_and_final_callback(monkeypatch, architecture):
    """Exercise the HTTP dispatch model through the actual comparison and callbacks."""
    from app.architectures import comparison

    request = build_request(architecture)
    request.experiment = request.experiment.model_copy(
        update={"comparisonProtocol": comparison.PROTOCOL_VERSION}
    )
    previous = request.latest_message.model_copy(
        update={
            "id": uuid4(),
            "direction": "outbound",
            "content_text": "Atendimento anterior: qual produto?",
        }
    )
    request.conversation_history = [previous, request.latest_message]
    # This round trip is how the JSON request reaches the runtime over HTTP.
    request = RuntimeDispatchRequest.model_validate_json(request.model_dump_json(by_alias=True))
    settings = Settings(enable_live_llm=True, llm_max_tokens=2048, aws_region="us-west-2")
    events, completions, contexts = [], [], []

    class FakeAgent:
        def __init__(self, ctx, role, tools, **kwargs):
            contexts.append(ctx)
            self.role = role

        def __call__(self, prompt):
            assert "outbound: Atendimento anterior: qual produto?" in prompt
            assert "inbound: Tem dipirona em estoque?" in prompt
            if self.role in {"router", "coordinator"}:
                return '{"routes":["stock"]}'
            return "Resposta final da execução de teste."

    monkeypatch.setattr(comparison, "ControlledAgent", FakeAgent)
    monkeypatch.setattr("app.services.callbacks.ChatApiCallbacks.emit_run_event", lambda self, event: events.append(event))
    monkeypatch.setattr("app.services.callbacks.ChatApiCallbacks.complete_run", lambda self, **kwargs: completions.append(kwargs))

    result = RuntimeExecutionService(settings).execute_run(request)

    assert all(ctx.settings is settings for ctx in contexts)
    assert result.total_tokens is None  # Never invent usage for a missing provider metric.
    final = next(e for e in events if e.event_family == "response" and e.event_name == "final")
    assert final.run_id == request.run_id
    assert final.payload["contentText"] == result.final_text
    assert final.payload["architectureMode"] == architecture
    assert final.payload["reviewRequired"] is False
    assert len(completions) == 1 and completions[0]["status"] == "completed"
    assert completions[0]["summary"].total_tokens is None


def test_comparison_service_reports_provider_failure_without_mock_response(monkeypatch):
    from app.architectures import comparison

    request = build_request()
    request.experiment = request.experiment.model_copy(
        update={"comparisonProtocol": comparison.PROTOCOL_VERSION}
    )
    events, completions = [], []

    class FailingAgent:
        def __init__(self, *args):
            raise RuntimeError("Provider unavailable")

    monkeypatch.setattr(comparison, "ControlledAgent", FailingAgent)
    monkeypatch.setattr("app.services.callbacks.ChatApiCallbacks.emit_run_event", lambda self, event: events.append(event))
    monkeypatch.setattr("app.services.callbacks.ChatApiCallbacks.complete_run", lambda self, **kwargs: completions.append(kwargs))

    with pytest.raises(RuntimeError, match="Provider unavailable"):
        RuntimeExecutionService(Settings(enable_live_llm=True)).execute_run(request)

    assert not any(e.event_family == "response" for e in events)
    assert len(completions) == 1
    assert completions[0]["status"] == "failed"
    assert completions[0]["final_outcome"] == "runtime_failed"


@pytest.mark.parametrize(("explicit_protocol", "explicit_profile", "expected_profile"), [
    (False, None, "application"),
    (True, None, "controlled-research"),
    (True, "application", "application"),
])
def test_live_v44_dispatch_preserves_the_intended_source_profile(monkeypatch, explicit_protocol, explicit_profile, expected_profile):
    from app.architectures import comparison_v44

    request = build_request()
    metadata = {"comparisonProtocol": comparison_v44.PROTOCOL_VERSION} if explicit_protocol else {}
    if explicit_profile is not None:
        metadata["comparisonSourceProfile"] = explicit_profile
    request.experiment = request.experiment.model_copy(update=metadata)
    request = RuntimeDispatchRequest.model_validate_json(request.model_dump_json(by_alias=True))
    calls = []
    result = object()

    def execute(ctx, architecture, *, source_profile):
        calls.append((ctx.request.run_id, architecture, source_profile))
        return result

    monkeypatch.setattr(comparison_v44, "execute_comparison_v44", execute)
    callback = type("TestCallbacks", (), {"emit_run_event": lambda self, event: None})()
    executor = RuntimeExecutor(request, settings=Settings(enable_live_llm=True), callbacks=callback)

    assert executor.execute() is result
    assert calls == [(request.run_id, "centralized_orchestration", expected_profile)]
