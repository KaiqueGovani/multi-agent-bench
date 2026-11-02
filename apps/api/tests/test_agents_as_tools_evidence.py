"""The API integration gate checks persisted evidence, not specialist claims."""
from copy import deepcopy
import importlib.util
from pathlib import Path

from app.schemas.domain import OperationalMetadata
from app.services.run_configuration import _build_run_experiment

_path = Path(__file__).resolve().parents[3] / "scripts" / "validate_agents_as_tools_api.py"
_spec = importlib.util.spec_from_file_location("api_agents_as_tools_validation", _path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def evidence():
    def event(n, family, name, actor, payload=None, tool=None):
        return {"id": f"event-{n}", "sequenceNo": n, "eventFamily": family,
                "eventName": name, "actorName": actor, "status": "completed",
                "payload": payload or {}, "toolName": tool}
    events = [
        event(1, "agent", "started", "supervisor", {"agentInvocationId": "supervisor-1"}),
        event(2, "agent", "started", "stock", {"agentInvocationId": "stock-1", "parentAgentInvocationId": "supervisor-1", "parentCallId": "specialist-tool"}),
        event(3, "model", "completed", "stock"),
        event(4, "tool", "started", "stock", {"toolCallId": "domain-tool", "input": {"question": "dipirona"}}, "stock_lookup"),
        event(5, "tool", "completed", "stock", {"toolCallId": "domain-tool", "result": {"product": "dipirona", "quantity": 17}}, "stock_lookup"),
        event(6, "communication", "message", "stock", {"to": "supervisor", "text": "Há 17 frascos."}),
        event(7, "response", "final", "supervisor"),
    ]
    run = {"id": "run-1", "status": "completed", "experiment": {"comparisonProtocol": "architectural-comparison-v4.2"}}
    execution = {"executionEvents": events, "run": run, "projection": {"runStatus": "completed"}}
    detail = {"messages": [{"direction": "outbound", "metadata": {"runtimeRunId": "run-1"}}]}
    return execution, detail


def test_api_dispatch_preserves_opt_in_protocol_without_forwarding_evaluation_data():
    metadata = OperationalMetadata.model_validate({"comparisonProtocol": "architectural-comparison-v4.2", "expectedAnswer": "private evaluation only"})
    experiment = _build_run_experiment(metadata, architecture_key="centralized_orchestration", comparison_only=False)
    serialized = experiment.model_dump(by_alias=True)
    assert serialized["comparisonProtocol"] == "architectural-comparison-v4.2"
    assert "expectedAnswer" not in serialized


def test_api_gate_rejects_specialist_without_actual_domain_source_completion():
    execution, detail = evidence()
    case = {"roles": ["stock"], "tools": ["stock_lookup"]}
    assert _module.verify(execution, detail, case, "architectural-comparison-v4.2")["passed"]
    no_domain = deepcopy(execution)
    no_domain["executionEvents"] = [e for e in no_domain["executionEvents"] if e["eventFamily"] != "tool"]
    checked = _module.verify(no_domain, detail, case, "architectural-comparison-v4.2")
    assert not checked["passed"]
    assert "completed required domain queries and results" in checked["failures"]


def test_api_gate_rejects_fabricated_agent_or_missing_return():
    execution, detail = evidence()
    execution["executionEvents"] = [e for e in execution["executionEvents"] if e["eventFamily"] not in ("model", "communication")]
    checked = _module.verify(execution, detail, {"roles": ["stock"], "tools": ["stock_lookup"]}, "architectural-comparison-v4.2")
    assert not checked["passed"]
    assert "physical model completion per specialist" in checked["failures"]
    assert "specialist results returned to supervisor" in checked["failures"]


def test_evidence_redacts_callback_keys_and_attachment_query_credentials():
    cleaned = _module.sanitized({"apiKey": "private", "retrievalUrl": "http://local/attachment?apiKey=private&x=1", "nested": [{"aiServiceSecret": "private"}]})
    assert "private" not in str(cleaned)
    assert "[REDACTED]" in str(cleaned)


def test_required_source_evidence_survives_an_extra_genuine_query():
    execution, detail = evidence()
    extra_start = {"id": "extra-start", "sequenceNo": 4.1, "eventFamily": "tool", "eventName": "started", "actorName": "stock", "status": "running", "toolName": "stock_lookup", "payload": {"toolCallId": "extra", "input": {"question": "ibuprofeno"}}}
    extra_end = {**extra_start, "id": "extra-end", "sequenceNo": 4.2, "eventName": "completed", "status": "completed", "payload": {"toolCallId": "extra", "result": {"product": "ibuprofeno", "quantity": 9}}}
    execution["executionEvents"].extend([extra_start, extra_end])
    assert _module.verify(execution, detail, {"roles": ["stock"], "tools": ["stock_lookup"]}, "architectural-comparison-v4.2")["passed"]


def test_tool_claim_with_unrelated_return_is_not_required_source_evidence():
    execution, detail = evidence()
    end = next(event for event in execution["executionEvents"] if event["eventFamily"] == "tool" and event["eventName"] == "completed")
    end["payload"]["result"] = {"product": "ibuprofeno", "quantity": 9}
    checked = _module.verify(execution, detail, {"roles": ["stock"], "tools": ["stock_lookup"]}, "architectural-comparison-v4.2")
    assert not checked["passed"]
    assert any("matching recorded arguments and return" in failure for failure in checked["failures"])
