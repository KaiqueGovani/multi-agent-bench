"""No live inference: audit counters, nesting, first-attempt preservation and blinding."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import run_research_pilot as collector
import judge_automated_pilots as judge
from app.experiments import methodology as m


def event(family, name, payload, actor="faq", tool=None, status="completed"):
    return {"eventFamily": family, "eventName": name, "payload": payload,
            "actorName": actor, "toolName": tool, "status": status}


def nested_events():
    return [
        event("agent", "started", {"callId": "super", "agentInvocationId": "super", "agentId": "super-instance"}, "supervisor"),
        event("model", "started", {"callId": "physical-1", "agentInvocationId": "super", "agentId": "super-instance"}, "supervisor"),
        event("model", "completed", {"callId": "physical-1", "usage": {"inputTokens": 10, "outputTokens": 2, "totalTokens": 12}}, "supervisor"),
        event("tool", "started", {"toolCallId": "delegate", "input": {"task": "Pix"}, "agentInvocationId": "super"}, "supervisor", "faq_specialist"),
        event("agent", "started", {"callId": "child", "agentInvocationId": "child", "parentCallId": "delegate", "agentId": "child-instance"}),
        event("model", "started", {"callId": "physical-2", "agentInvocationId": "child", "agentId": "child-instance"}),
        event("model", "completed", {"callId": "physical-2", "usage": {"inputTokens": 20, "outputTokens": 3, "totalTokens": 23}}),
        event("agent", "completed", {"callId": "child", "totalTokens": 23, "outputText": "Pix aceito"}),
        event("tool", "completed", {"toolCallId": "delegate", "result": {"result": "Pix aceito"}}, "supervisor", "faq_specialist"),
        event("model", "started", {"callId": "physical-3", "agentInvocationId": "super", "agentId": "super-instance"}, "supervisor"),
        event("model", "completed", {"callId": "physical-3", "usage": {"inputTokens": 30, "outputTokens": 4, "totalTokens": 34}}, "supervisor"),
        # An SDK parent's inclusive usage must never be added to physical usage.
        event("agent", "completed", {"callId": "super", "totalTokens": 99999}, "supervisor"),
        event("architecture", "contract", {"compliant": True, "violations": []}, "supervisor"),
        event("response", "final", {"text": "Aceitamos Pix"}, "supervisor"),
    ]


def test_physical_ledger_reconciles_without_parent_sdk_double_counting():
    result = collector.trace_measurements(nested_events())
    assert result["total_tokens"] == 69
    assert result["input_tokens"] == 60 and result["output_tokens"] == 9
    assert result["actual_agents"] == result["agent_invocations"] == 2
    assert result["model_requests"] == 3 and result["specialist_tool_invocations"] == 1
    assert result["domain_tool_calls"] == 0 and result["coordination_tool_calls"] == 1
    assert result["token_measurement_complete"]


def test_partial_usage_and_duplicate_physical_ids_never_become_zero_or_double_sum():
    events = nested_events()
    events = [e for e in events if not (e["eventFamily"] == "model" and e["eventName"] == "completed" and e["payload"]["callId"] == "physical-3")]
    result = collector.trace_measurements(events)
    assert result["total_tokens"] is None and result["known_partial_total_tokens"] == 35
    events = nested_events()
    events.append(copy.deepcopy(events[2]))
    result = collector.trace_measurements(events)
    assert not result["provider_call_ids_unique"] and result["total_tokens"] is None
    assert result["known_partial_total_tokens"] == 69


def test_architecture_requires_actual_child_model_and_return_before_final():
    events = nested_events()
    assert collector.verify_architectural_trace("centralized_orchestration", events)["compliant"]
    events = [e for e in events if not (e["eventFamily"] == "model" and e["payload"].get("agentInvocationId") == "child")]
    assert "specialist_without_physical_model_request" in collector.verify_architectural_trace("centralized_orchestration", events)["violations"]
    events = nested_events()
    events[8], events[-1] = events[-1], events[8]
    assert not collector.verify_architectural_trace("centralized_orchestration", events)["compliant"]


def test_specialist_name_without_source_call_cannot_satisfy_mandatory_source():
    case = json.loads((ROOT / "experiments/pilots-v5/pilot-b.json").read_text())["cases"][0]
    run = {"success": True, "comparison_protocol": "architectural-comparison-v4.2", "architectural_compliance": True}
    objective = m.objective_checks(case, run, nested_events())
    assert objective["procedure_compliance"] is False
    from app.tools.research_tools import faq_lookup
    source = [
        event("tool", "started", {"toolCallId": "source", "input": {"question": "pagamento Pix"}, "agentInvocationId": "child"}, tool="faq_lookup"),
        event("tool", "completed", {"toolCallId": "source", "result": faq_lookup(question="pagamento Pix"), "agentInvocationId": "child"}, tool="faq_lookup"),
    ]
    events = nested_events()
    events[7:7] = source
    assert m.objective_checks(case, run, events)["procedure_compliance"] is True
    source[1]["payload"]["agentInvocationId"] = "invented"
    assert m.objective_checks(case, run, events)["procedure_compliance"] is False


def test_contract_violation_fails_task_without_mutating_semantic_judgment():
    case = json.loads((ROOT / "experiments/pilots-v5/pilot-b.json").read_text())["cases"][6]
    objective = {"required_evidence": [], "critical_violations": []}
    assert m.aggregate(case, {"success": True, "architectural_compliance": False}, objective, None) == {
        "task_success": False, "reason": "architectural contract violation"}
    assert m.aggregate(case, {"success": True, "comparison_protocol": "architectural-comparison-v4.2"}, objective, None)["task_success"] is None


def test_new_six_case_pilot_is_predeclared_and_reference_hashes_remain_valid():
    catalogue = json.loads((ROOT / "experiments/corrected-comparison-v4.2/pilot-six.json").read_text())
    m.validate_catalogue(catalogue)
    assert len(catalogue["cases"]) == 6 and len(catalogue["coverage"]) == 6
    order = collector.build_order(catalogue["cases"], 1, 20261011, "00000000-0000-0000-0000-000000000001")
    assert len(order) == 18 and len({u["unit_id"] for u in order}) == 18


def test_stability_selection_is_fixed_before_outcomes_and_never_replaced():
    cases = [{"id": str(i), "stratum": stratum, "difficulty": "low"} for i, stratum in enumerate(("faq", "stock", "attachments", "professional_review", "continuity"))]
    order = collector.build_order(cases, 5, 20261011, "00000000-0000-0000-0000-000000000001")
    plan = collector.stability_plan(order)
    assert len(plan["unit_ids"]) == len(set(plan["unit_ids"])) == 15
    assert plan == collector.stability_plan(order)
    runs = [{"unit_id": uid, "attempt_id": uid} for uid in plan["unit_ids"]]
    mapping = {"blind-" + uid: uid for uid in plan["unit_ids"][1:]}
    selected = judge.select_rechecks({"stability_recheck_plan": plan}, [], mapping, runs)
    assert len(selected) == 14 and all("blind-" + uid in selected for uid in plan["unit_ids"][1:])


def test_dead_first_attempt_is_preserved_without_inference(tmp_path):
    collector.dump(tmp_path / "task.json", {"attempt_id": "original"})
    collector.dump(tmp_path / "launch.json", {})
    (tmp_path / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in nested_events()[:2]))
    result = collector.preserve_interrupted_attempt(tmp_path, {"unit_id": "unit"})
    assert result["attempt_id"] == "original" and result["status"] == "interrupted"
    assert result["model_requests"] == 1 and result["total_tokens"] is None
    assert json.loads((tmp_path / "result.json").read_text()) == result


def test_frozen_semantic_judge_prompt_is_exactly_historical():
    assert judge.config()["prompt_sha256"] == "ac77d9d9800bd6830102e5760a4d848330c3bcfcfa6d65b7d5723713f9478e36"


def test_interrupted_judgment_is_unknown_without_another_provider_request(tmp_path, monkeypatch):
    calibration = tmp_path / "calibration"
    calibration.mkdir()
    folder = tmp_path / "experiment"
    folder.mkdir()
    collector.dump(calibration / "calibration-gate.json", {"passed": True})
    collector.dump(calibration / "judge-config.json", {})
    collector.dump(folder / "manifest.json", {"order": [{"unit_id": "unit"}]})
    collector.append(folder / "runs.jsonl", {"unit_id": "unit"})
    case = json.loads((ROOT / "experiments/pilots-v5/pilot-b.json").read_text())["cases"][0]
    collector.dump(folder / "blind-responses.json", [{"evaluation_id": "blind", "input": case, "response": "Resposta"}])
    collector.append(folder / "judge-attempts.jsonl", {"event": "started", "phase": "primary", "response_id": "blind", "attempt_id": "first"})
    monkeypatch.setattr(judge, "frozen_config", lambda *a: None)
    def forbidden(*a, **kw):
        raise AssertionError("A started primary judgment cannot be replaced")
    monkeypatch.setattr(judge, "converse", forbidden)
    assert judge.evaluate_folder(folder, {}, calibration, False)
    failure = judge.read_jsonl(folder / "evaluation-failures.jsonl")[0]
    assert failure["reason"] == "interrupted_prior_judgment_preserved_no_replacement"
    assert not judge.read_jsonl(folder / "evaluations.jsonl")
