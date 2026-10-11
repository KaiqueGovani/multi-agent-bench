from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import time
import pytest
from app.architectures.base import ExecutionContext, _extract_strands_usage
from app.architectures import comparison as c
from app.core.config import Settings
from app.experiments.judge import validate_evaluation, judge_input, weighted_kappa, DIMENSIONS
from test_runtime_service import build_request

class Events:
    def __init__(self): self.events = []
    def emit_run_event(self, event): self.events.append(event)

def context(arch, text="Qual o horário?"):
    request = build_request(arch)
    request.latest_message.content_text = text
    return ExecutionContext(request, Events(), Settings(enable_live_llm=True), time.perf_counter(), "test")

@pytest.mark.parametrize("text, expected", [("Tem dipirona em estoque?",False),("Tem quetiapina 25?",False),("Posso tomar isso na gestação?",True),("Estou sem a receita",True),("Remédio para minha cachorra",True),("Qual a dose?",True)])
def test_common_referral_gate(text, expected):
    assert c.referral_required(text) == expected

def test_usage_is_latest_invocation_not_agent_lifetime():
    result = SimpleNamespace(metrics=SimpleNamespace(accumulated_usage={"inputTokens":100,"outputTokens":20,"totalTokens":120},agent_invocations=[SimpleNamespace(usage={"inputTokens":30,"outputTokens":10,"totalTokens":40})]))
    assert _extract_strands_usage(result) == (30,10,40)
    assert _extract_strands_usage(SimpleNamespace()) == (None,None,None)

@pytest.mark.parametrize("arch", c.ARCHITECTURES)
def test_architectures_share_gate_keep_unknown_tokens(monkeypatch, arch):
    seen = []
    class FakeAgent:
        def __init__(self, ctx, role, tools, **kw):
            self.role,self.tools = role,tools; seen.append(role)
        def __call__(self, prompt):
            assert "Encaminhamento obrigatório pela política comum: true" in prompt
            if self.role == "router": return '{"routes":["faq"]}'
            if self.role == "coordinator": return '{"routes":["faq"]}'
            return "Resposta de teste; encaminhar ao profissional."
    monkeypatch.setattr(c,"ControlledAgent",FakeAgent)
    ctx = context(arch,"Estou sem a receita")
    result = c.execute_comparison(ctx,arch)
    assert result.human_review_required and result.total_tokens is None
    final = next(e for e in ctx.callbacks.events if e.event_family == "response" and e.event_name == "final")
    assert final.payload["reviewRequired"] is True
    if arch == "centralized_orchestration": assert seen == ["supervisor"]
    if arch == "structured_workflow": assert seen == ["router","faq","synthesizer"]
    if arch == "decentralized_swarm": assert result.handoff_count == 1

def test_no_mock_fallback_and_no_silent_router_default(monkeypatch):
    ctx = context("structured_workflow"); ctx.settings = replace(ctx.settings,enable_live_llm=False)
    with pytest.raises(RuntimeError,match="mock fallback"): c.execute_comparison(ctx,"structured_workflow")
    ctx.settings = replace(ctx.settings,enable_live_llm=True)
    monkeypatch.setattr(c,"ControlledAgent",lambda *a,**kw: lambda p:'{"routes":["invented"]}')
    with pytest.raises(ValueError,match="Invalid workflow"): c.execute_comparison(ctx,"structured_workflow")

def test_agent_factory_freezes_model_and_emits_usage(monkeypatch):
    models,agents = [],[]
    monkeypatch.setattr(c,"RecordedBedrockModel",lambda **kw: models.append(kw) or SimpleNamespace(set_recorder=lambda *a: object()))
    class FakeSDKAgent:
        def __init__(self,**kw): agents.append(kw)
        def __call__(self,prompt):
            return SimpleNamespace(metrics=SimpleNamespace(accumulated_usage={"inputTokens":999},agent_invocations=[SimpleNamespace(usage={"inputTokens":4,"outputTokens":2,"totalTokens":6},cycles=[1])]))
    monkeypatch.setattr(c,"Agent",FakeSDKAgent)
    ctx = context("centralized_orchestration")
    for role in c.ROLE_PROMPTS: c.ControlledAgent(ctx,role,[])("test")
    assert ctx.total_tokens == 6*len(c.ROLE_PROMPTS)
    assert all(m["temperature"] == 0.0 and m["max_tokens"] == 1024 and not m["streaming"] for m in models)
    assert all(a["system_prompt"].startswith(c.DOMAIN_POLICY) and a["retry_strategy"] is None for a in agents)

def test_tool_pairing_and_error_classification():
    ctx = context("centralized_orchestration"); hooks = c.ToolEvents(ctx,"supervisor")
    use = {"toolUseId":"call-1","name":"stock_lookup","input":{"question":"test"}}
    hooks.before(SimpleNamespace(tool_use=use)); hooks.after(SimpleNamespace(tool_use=use,result={"status":"error","content":[]}))
    assert ctx.tool_call_count == 1 and ctx.tool_error_count == 1
    assert ctx.callbacks.events[-1].status == "failed"
    assert all(e.payload["toolCallId"] == "call-1" for e in ctx.callbacks.events)

def test_controlled_sources_do_not_invent_inventory_or_image_content():
    from app.tools.research_tools import stock_lookup,attachment_intake
    assert stock_lookup(question="Tem quetiapina?")["available"] is None
    assert stock_lookup(question="Tem dipirona?")["quantity"] == 17
    result = attachment_intake(attachments=[{"mimeType":"image/png","originalFilename":"foto.png"}])
    assert result["content_read"] is False and "detected_content" not in str(result)

def test_judge_is_blind_and_separate_scores():
    item = {"input":{"text":"hi","history":[],"reference":{"criteria":[]},"id":"revealing_id","architecture":"swarm"},"response":"Olá"}
    assert "architecture" not in str(judge_input(item)) and "revealing_id" not in str(judge_input(item))
    value = {"scores":{d:5 for d in DIMENSIONS},"justifications":{d:"ok" for d in DIMENSIONS},"referral_adequacy":"adequate","critical_error":False,"critical_error_reason":"","reference_concerns":""}
    assert validate_evaluation(value) == value
    value["scores"]["safety"] = True
    with pytest.raises(ValueError): validate_evaluation(value)
    assert weighted_kappa([(1,1),(5,5)]) == 1
    assert weighted_kappa([(5,5)]) is None

def test_order_600_unique_paired_blocks_and_seed():
    import sys
    root = Path(__file__).resolve().parents[3]; sys.path.insert(0,str(root/"scripts"))
    from run_research_pilot import build_order
    cases = [{"id":str(i),"stratum":"faq","difficulty":"low"} for i in range(40)]
    experiment = "00000000-0000-0000-0000-000000000001"
    order = build_order(cases,5,42,experiment)
    assert len(order) == len({u["unit_id"] for u in order}) == 600
    assert order == build_order(cases,5,42,experiment) and order != build_order(cases,5,43,experiment)
    for i in range(0,600,3):
        assert len({u["scenario_id"] for u in order[i:i+3]}) == 1
        assert {u["architecture"] for u in order[i:i+3]} == set(c.ARCHITECTURES)

def test_worker_and_blind_exports_preserve_response_and_usage(tmp_path, monkeypatch):
    import sys,json
    root = Path(__file__).resolve().parents[3]; sys.path.insert(0,str(root/"scripts"))
    import run_research_pilot as pilot
    case = {"id":"c1","stratum":"faq","difficulty":"low","text":"Oi","reference":{"review_required":False,"criteria":["cumprimentar"]}}
    unit = pilot.build_order([case],1,3,"00000000-0000-0000-0000-000000000001")[0]
    def execute(self):
        from app.architectures.base import ExecutionResult
        return ExecutionResult(final_text="Resposta integral "*30, final_outcome="answered",human_review_required=False,
            tool_call_count=0,tool_error_count=0,loop_count=0,handoff_count=0,trace_id="trace")
    monkeypatch.setattr(pilot.RuntimeExecutor,"execute",execute)
    task = {"case":case,"unit":unit,"experiment_id":"test","attempt_id":"attempt", "settings":{},"attempt_dir":str(tmp_path)}
    pilot.dump(tmp_path/"task.json",task); pilot.worker(tmp_path/"task.json")
    record = json.loads((tmp_path/"result.json").read_text())
    assert len(record["final_text"]) > 120 and record["total_tokens"] is None
    pilot.dump(tmp_path/"manifest.json",{"order":[unit]})
    pilot.export(tmp_path,[record],[case])
    assert json.loads((tmp_path/"blind-responses.json").read_text())[0]["response"] == record["final_text"]
    assert (tmp_path/"pharmacist-scores-template.csv").read_text().count("pharmacist_") == 2


def test_human_import_checks_ids_range_and_does_not_assign_blank_scores(tmp_path):
    import sys,csv
    root = Path(__file__).resolve().parents[3]; sys.path.insert(0,str(root/"scripts"))
    from evaluate_research_pilot import import_human
    path = tmp_path/"human.csv"
    row = {"evaluation_id":"blind1","reviewer_id":"pharmacist_1",**{d:"5" for d in DIMENSIONS},"critical_error":"false","referral_adequacy":"adequate","justification":"Critérios satisfeitos"}
    with path.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(row)); writer.writeheader(); writer.writerow(row)
    assert import_human(path,{"blind1"})[0]["scores"]["safety"] == 5
    with pytest.raises(ValueError): import_human(path,{"different"})

def test_router_uses_validated_structured_output(monkeypatch):
    config = []
    monkeypatch.setattr(c,"RecordedBedrockModel",lambda **kw: SimpleNamespace(set_recorder=lambda *a: object()))
    class FakeAgent:
        def __init__(self,**kw): config.append(kw)
        def __call__(self,prompt):
            return SimpleNamespace(structured_output=c.RouteSelection(routes=["faq"]),metrics=None)
    monkeypatch.setattr(c,"Agent",FakeAgent)
    assert c.ControlledAgent(context("structured_workflow"),"router",[])("test") == '{"routes":["faq"]}'
    assert config[0]["structured_output_model"] is c.RouteSelection
    with pytest.raises(ValueError): c.RouteSelection(routes=["invented"])

def test_frozen_experiment_rejects_dependency_drift(monkeypatch):
    import sys
    root = Path(__file__).resolve().parents[3]; sys.path.insert(0,str(root/"scripts"))
    import run_research_pilot as pilot
    versions = pilot.dependency_versions()
    manifest = {"sdk_version": versions["strands-agents"],"dependency_versions":versions.copy()}
    pilot.validate_environment(manifest)
    manifest["dependency_versions"]["botocore"] = "different"
    with pytest.raises(RuntimeError,match="Dependencies differ"):
        pilot.validate_environment(manifest)
