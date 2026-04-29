from uuid import uuid4

from app.schemas.runtime import (
    OperationalMetadata,
    RunExperimentMetadata,
    RuntimeCallbackConfig,
    RuntimeDispatchRequest,
    RuntimeMessageSnapshot,
)
from app.services.execution import RuntimeExecutionService


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
