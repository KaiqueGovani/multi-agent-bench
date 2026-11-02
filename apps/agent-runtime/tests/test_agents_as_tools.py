"""Architecture tests run real Strands agents against controlled provider responses."""
from dataclasses import replace
import json
from types import SimpleNamespace
import pytest
from strands.models.bedrock import BedrockModel
from app.architectures import comparison as c
from test_research_comparison import context


def scripted_provider(monkeypatch, routes=("faq",), *, omit_domain=False, omit_delegation=False, repeat=1, fail_role=None, extra_usage=False):
    calls, instances = [], []
    original_init = BedrockModel.__init__
    def init(self, **kwargs):
        # Keep the installed SDK request formatting/event conversion, replace only network client.
        self.config = {**kwargs, "include_tool_result_status":"auto"}
        self.config.pop("boto_client_config",None)
        self.config.pop("region_name",None)
        self.client = SimpleNamespace(converse=lambda **request: response(self,request))
        instances.append(self)
    def response(model, request):
        role = model.role
        own = [x for x in calls if x["role"]==role and x["model_instance"]==id(model)]
        calls.append({"model_instance":id(model),"role":role,"request":request,"agent_id":c.active_invocation(model.ctx).get("agentId")})
        if role == fail_role:
            raise RuntimeError("controlled provider failure")
        if role in {"router","coordinator"}:
            # Strands 1.37 structured output is a physical request using its output tool.
            spec = request.get("toolConfig",{}).get("tools",[])
            if spec:
                output_name = spec[-1]["toolSpec"]["name"]
                content=[{"toolUse":{"toolUseId":f"route-{len(calls)}","name":output_name,"input":{"routes":list(routes)}}}]
                stop="tool_use"
            else:
                content=[{"text":json.dumps({"routes":list(routes)})}];stop="end_turn"
        elif role == "supervisor" and not omit_delegation and len(own) < repeat:
            content=[{"toolUse":{"toolUseId":f"delegate-{len(calls)}-{r}","name":r+"_specialist","input":{"task":"colete as evidências originais"}}} for r in routes]
            stop="tool_use"
        elif role in c.TOOLS and not omit_domain and not any("toolResult" in x for m in request["messages"] for x in m["content"]):
            name = c.TOOLS[role].tool_spec["name"]
            args = {"attachments":[{"attachmentId":"attachment-1","originalFilename":"foto.png","mimeType":"image/png","sizeBytes":20}]} if role == "attachments" else {"question":"horario" if role == "faq" else "dipirona"}
            content=[{"toolUse":{"toolUseId":f"domain-{len(calls)}","name":name,"input":args}}];stop="tool_use"
        else:
            content=[{"text":"Evidências verificadas: atendimento 08:00 a 22:00; dipirona 17 frascos; anexos somente metadados."}];stop="end_turn"
        return {"output":{"message":{"role":"assistant","content":content}},"stopReason":stop,
                "usage":{"inputTokens":7,"outputTokens":3,"totalTokens":10},"metrics":{"latencyMs":1}}
    monkeypatch.setattr(BedrockModel,"__init__",init)
    return calls, instances


@pytest.mark.parametrize("routes",[("faq",),("stock",),("attachments",),("faq","stock","attachments")])
def test_real_supervisor_tool_invokes_real_specialists_and_receives_return(monkeypatch,routes):
    calls,instances=scripted_provider(monkeypatch,routes)
    ctx=context("centralized_orchestration")
    result=c.execute_comparison(ctx,"centralized_orchestration")
    events=ctx.callbacks.events
    supervisor_call=next(x for x in calls if x["role"]=="supervisor")
    assert {x["toolSpec"]["name"] for x in supervisor_call["request"]["toolConfig"]["tools"]} == c.SPECIALIST_NAMES
    assert not c.DOMAIN_NAMES.intersection(x["toolSpec"]["name"] for x in supervisor_call["request"]["toolConfig"]["tools"])
    assert {x["role"] for x in calls} == {"supervisor",*routes}
    assert result.specialist_tool_invocations==len(routes) and result.architectural_compliance
    last_supervisor=next(x for x in reversed(calls) if x["role"]=="supervisor")
    assert any("toolResult" in x for m in last_supervisor["request"]["messages"] for x in m["content"])
    starts={e.payload["callId"]:e for e in events if e.event_family=="agent" and e.event_name=="started"}
    for e in starts.values():
        if e.actor_name in routes:
            assert e.payload["parentAgentInvocationId"] in starts
            assert e.payload["parentCallId"].startswith("delegate-")
    assert result.total_tokens==10*len(calls) and result.input_tokens==7*len(calls)
    assert result.model_requests==len(calls) and result.domain_tool_calls==len(routes)
    assert result.coordination_tool_calls==len(routes)
    final_index=next(i for i,e in enumerate(events) if e.event_family=="response" and e.event_name=="final")
    assert all(i<final_index for i,e in enumerate(events) if e.event_family=="agent" and e.event_name=="completed")


def test_no_delegation_preserves_answer_but_records_contract_violation(monkeypatch):
    calls,_=scripted_provider(monkeypatch,omit_delegation=True)
    ctx=context("centralized_orchestration")
    result=c.execute_comparison(ctx,"centralized_orchestration")
    assert result.final_text and result.architectural_compliance is False
    assert result.specialist_tool_invocations==0
    assert [x["role"] for x in calls]==["supervisor"]
    assert not any(e.event_family=="tool" for e in ctx.callbacks.events)
    assert any(e.event_family=="architecture" and e.status=="failed" for e in ctx.callbacks.events)


def test_nested_limits_and_errors_are_global(monkeypatch):
    calls,_=scripted_provider(monkeypatch,repeat=7)
    ctx=context("centralized_orchestration")
    with pytest.raises(c.ExperimentLimitExceeded):c.execute_comparison(ctx,"centralized_orchestration")
    assert ctx.specialist_tool_invocations==6 and ctx.research_model_calls<=20
    assert not ctx.invocation_stack
    assert any(e.event_family=="limit" for e in ctx.callbacks.events)


def test_physical_request_limit_prevents_nested_request(monkeypatch):
    calls,_=scripted_provider(monkeypatch)
    ctx=context("centralized_orchestration");ctx.research_model_calls=19
    with pytest.raises(c.ExperimentLimitExceeded):c.execute_comparison(ctx,"centralized_orchestration")
    assert len(calls)==1 and ctx.research_model_calls==20
    assert not ctx.invocation_stack


def test_isolation_and_common_specialist_definitions(monkeypatch):
    calls,instances=scripted_provider(monkeypatch,repeat=2)
    a=context("centralized_orchestration");b=context("centralized_orchestration","Independent scenario")
    c.execute_comparison(a,"centralized_orchestration");c.execute_comparison(b,"centralized_orchestration")
    a_ids={v["agentId"] for v in a.provider_requests.values()};b_ids={v["agentId"] for v in b.provider_requests.values()}
    assert not a_ids.intersection(b_ids)
    assert len({x["agent_id"] for x in calls if x["role"]=="faq"})==2
    for ctx in (a,b):
        assert not ctx.invocation_stack and not ctx.tool_stack
        starts=[e for e in ctx.callbacks.events if e.event_family=="agent" and e.event_name=="started"]
        assert all("reference" not in e.payload["inputText"] and "criteria" not in e.payload["inputText"] for e in starts)
    definition=c.snapshot(a.settings)["specialist_definition_hashes"]
    assert set(definition)==set(c.TOOLS)


def test_global_deadline_rejects_without_model_request(monkeypatch):
    calls,_=scripted_provider(monkeypatch)
    ctx=context("centralized_orchestration");ctx.started_at-=200
    with pytest.raises(c.ExperimentLimitExceeded,match="deadline"):c.execute_comparison(ctx,"centralized_orchestration")
    assert not calls


def test_failed_physical_request_usage_stays_unknown(monkeypatch):
    calls,_=scripted_provider(monkeypatch,fail_role="faq")
    ctx=context("centralized_orchestration")
    # SDK tool exception is visible to supervisor; physical request failure cannot become a zero.
    result=c.execute_comparison(ctx,"centralized_orchestration")
    assert result.total_tokens is None and not result.token_measurement_complete
    assert any(r["status"]=="failed" for r in ctx.provider_requests.values())


@pytest.mark.parametrize("arch",["structured_workflow","decentralized_swarm"])
def test_shared_specialists_use_same_prompt_and_tools_in_other_plans(monkeypatch,arch):
    calls,instances=scripted_provider(monkeypatch,routes=("stock",))
    ctx=context(arch)
    result=c.execute_comparison(ctx,arch)
    assert result.architectural_compliance
    specialist=next(x for x in calls if x["role"]=="stock")
    assert specialist["request"]["system"]==[{"text":c.DOMAIN_POLICY+"\n"+c.ROLE_PROMPTS["stock"]+(c.PEER_INSTRUCTION if arch=="decentralized_swarm" else "")}]
    names={x["toolSpec"]["name"] for x in specialist["request"]["toolConfig"]["tools"]}
    assert names==({"stock_lookup","handoff_to_peer"} if arch=="decentralized_swarm" else {"stock_lookup"})
    assert result.total_tokens==10*len(calls)


def test_no_domain_call_is_not_objective_source_evidence(monkeypatch):
    scripted_provider(monkeypatch,omit_domain=True)
    ctx=context("centralized_orchestration")
    result=c.execute_comparison(ctx,"centralized_orchestration")
    assert result.specialist_tool_invocations==1 and result.domain_tool_calls==0
    assert not any(e.tool_name in c.DOMAIN_NAMES for e in ctx.callbacks.events)


def test_application_and_comparison_share_agent_topology(monkeypatch):
    from app.services.execution import RuntimeExecutor
    scripted_provider(monkeypatch,routes=("stock",))
    app=context("centralized_orchestration")
    result=RuntimeExecutor(app.request,settings=app.settings,callbacks=app.callbacks).execute()
    assert result.specialist_tool_invocations==1 and result.architectural_compliance
    configuration=next(e.payload for e in app.callbacks.events if e.event_family=="experiment")
    assert configuration["sources_profile"]=="application"
    assert any("application-controlled-poc-adapter" in str(e.payload) for e in app.callbacks.events if e.event_family=="tool" and e.event_name=="completed")
