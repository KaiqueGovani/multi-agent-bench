"""Controlled Converse tests for the v4.4 executor scope and v4.2 comparators."""
from collections import deque
from types import SimpleNamespace
from uuid import uuid4

import pytest
from strands.models.bedrock import BedrockModel

from app.architectures import comparison as v42
from app.architectures import comparison_v44 as v44
from app.schemas.runtime import RuntimeAttachmentDescriptor
from test_agents_as_tools import scripted_provider
from test_research_comparison import context


def provider(monkeypatch, *steps):
    script = deque(steps)
    requests = []

    def initialize(model, **kwargs):
        model.config = {k: v for k, v in kwargs.items() if k not in {"boto_client_config", "region_name"}}
        model.config["include_tool_result_status"] = "auto"
        model.client = SimpleNamespace(converse=lambda **request: converse(model, request))

    def converse(model, request):
        requests.append((model.role, request))
        expected_role, content = script.popleft()
        assert model.role == expected_role
        if isinstance(content, str):
            content = [{"text": content}]
        return {
            "output": {"message": {"role": "assistant", "content": content}},
            "stopReason": "tool_use" if any("toolUse" in block for block in content) else "end_turn",
            "usage": {"inputTokens": 7, "outputTokens": 3, "totalTokens": 10},
            "metrics": {"latencyMs": 1},
        }

    monkeypatch.setattr(BedrockModel, "__init__", initialize)
    return requests, script


def tool_use(name, tool_call_id, **arguments):
    return {"toolUse": {"toolUseId": tool_call_id, "name": name, "input": arguments}}


def attach(ctx):
    message = ctx.request.latest_message
    message.attachments = [RuntimeAttachmentDescriptor(
        attachment_id=uuid4(), message_id=message.id, original_filename="foto.png",
        mime_type="image/png", size_bytes=20, checksum="synthetic", retrieval_url="http://private.invalid/restricted",
    )]


def events(ctx, family, name):
    return [e for e in ctx.callbacks.events if e.event_family == family and e.event_name == name]


def offered_tools(request):
    return {t["toolSpec"]["name"] for t in request["toolConfig"]["tools"]}


@pytest.mark.parametrize("attachments_first", [False, True])
def test_same_turn_out_of_scope_tool_cannot_dispatch_even_after_attachment_result(monkeypatch, attachments_first):
    attach_tool = tool_use("attachments_specialist", "attachment-request", task="anexo")
    early_stock = tool_use("stock_specialist", "blocked-stock", task="estoque antes da etapa permitida")
    first = [attach_tool, early_stock] if attachments_first else [early_stock, attach_tool]
    requests, script = provider(monkeypatch,
        ("supervisor", first),
        ("attachments", [tool_use("attachment_intake", "read-metadata", attachments=[{"attachmentId": "attachment-1"}])]),
        ("attachments", "Resultado do especialista de anexos"),
        ("supervisor", [tool_use("stock_specialist", "later-stock", task="estoque agora")]),
        ("stock", [tool_use("stock_lookup", "look-up-stock", question="dipirona")]),
        ("stock", "Resultado do especialista de estoque"),
        ("supervisor", "Resposta final do supervisor"),
    )
    ctx = context("centralized_orchestration", "Considere a foto e confira o estoque")
    attach(ctx)
    result = v44.execute_comparison_v44(ctx, "centralized_orchestration")
    assert not script
    supervisor = [request for role, request in requests if role == "supervisor"]
    assert [request["toolConfig"]["toolChoice"] for request in supervisor] == [{"any": {}}, {"auto": {}}, {"auto": {}}]
    assert offered_tools(supervisor[0]) == {"attachments_specialist"}
    assert offered_tools(supervisor[1]) == v42.SPECIALIST_NAMES
    second_results = [block["toolResult"] for message in supervisor[1]["messages"]
                      for block in message["content"] if "toolResult" in block]
    assert [(item["toolUseId"], item["status"]) for item in second_results].count(("blocked-stock", "error")) == 1
    assert [e.actor_name for e in events(ctx, "agent", "started")] == ["supervisor", "attachments", "stock"]
    rejected, = events(ctx, "tool", "rejected")
    assert rejected.tool_name == "stock_specialist" and rejected.payload["toolCallId"] == "blocked-stock"
    assert rejected.payload["supervisorModelTurn"] == 1
    assert all(e.payload.get("toolCallId") != "blocked-stock" for e in ctx.callbacks.events if e.event_family == "tool"
               and e.event_name in {"started", "completed"})
    assert [e.tool_name for e in events(ctx, "tool", "started")] == [
        "attachments_specialist", "attachment_intake", "stock_specialist", "stock_lookup"]
    contract, = events(ctx, "architecture", "contract")
    assert contract.payload["scopeRejectedToolRequests"] == 1 and contract.payload["attachmentSpecialistCompleted"]
    assert result.architectural_compliance and result.specialist_tool_invocations == 2
    assert result.model_requests == 7 and result.total_tokens == 70
    assert result.domain_tool_calls == result.coordination_tool_calls == 2
    assert events(ctx, "response", "final")[0].actor_name == "supervisor"


def test_rejection_without_mandatory_child_preserves_scope_on_next_turn(monkeypatch):
    requests, script = provider(monkeypatch,
        ("supervisor", [tool_use("stock_specialist", "illegal-first", task="estoque")]),
        ("supervisor", [tool_use("attachments_specialist", "attach-next", task="anexo")]),
        ("attachments", "Metadados do anexo"),
        ("supervisor", "Resposta"),
    )
    ctx = context("centralized_orchestration")
    attach(ctx)
    assert v44.execute_comparison_v44(ctx, "centralized_orchestration").architectural_compliance
    assert not script
    supervisor = [request for role, request in requests if role == "supervisor"]
    assert [request["toolConfig"]["toolChoice"] for request in supervisor] == [{"any": {}}, {"any": {}}, {"auto": {}}]
    assert [offered_tools(request) for request in supervisor] == [{"attachments_specialist"}, {"attachments_specialist"}, v42.SPECIALIST_NAMES]
    assert [e.actor_name for e in events(ctx, "agent", "started")] == ["supervisor", "attachments"]


@pytest.mark.parametrize("has_attachment", [False, True])
def test_unverified_final_is_preserved_as_rejected_candidate(monkeypatch, has_attachment):
    requests, script = provider(monkeypatch, ("supervisor", "Candidato sem especialista"))
    ctx = context("centralized_orchestration")
    if has_attachment:
        attach(ctx)
    result = v44.execute_comparison_v44(ctx, "centralized_orchestration")
    assert not script and len(requests) == 1 and not result.architectural_compliance
    assert requests[0][1]["toolConfig"]["toolChoice"] == {"any": {}}
    if not has_attachment:
        assert offered_tools(requests[0][1]) == v42.SPECIALIST_NAMES
    assert result.final_outcome == "architectural_contract_failed"
    assert result.final_text == "Candidato sem especialista"
    assert "no_completed_specialist_with_physical_request" in result.architectural_violations
    assert ("attachment_specialist_not_completed" in result.architectural_violations) == has_attachment
    assert not events(ctx, "response", "final")
    assert len(events(ctx, "response", "rejected")) == 1


@pytest.mark.parametrize("architecture", ["structured_workflow", "decentralized_swarm"])
@pytest.mark.parametrize("has_attachment", [False, True])
def test_noncentral_branch_has_same_physical_requests_and_authority_as_v42(monkeypatch, architecture, has_attachment):
    observed = []
    for execute, protocol in ((v42.execute_comparison, v42.PROTOCOL_VERSION),
                              (v44.execute_comparison_v44, v44.PROTOCOL_VERSION)):
        calls, _ = scripted_provider(monkeypatch, routes=("stock",))
        ctx = context(architecture)
        if has_attachment:
            attach(ctx)
        result = execute(ctx, architecture)
        configuration, = events(ctx, "experiment", "configuration")
        assert configuration.payload["protocol"] == protocol
        final, = events(ctx, "response", "final")
        observed.append(([(call["role"], call["request"]) for call in calls], result.model_requests,
                         result.domain_tool_calls, result.coordination_tool_calls, result.total_tokens,
                         result.handoff_count, final.actor_name))
    assert observed[0] == observed[1]
    assert observed[1][-1] == "synthesizer"
    assert observed[1][0][0][0] == ("router" if architecture == "structured_workflow" else "coordinator")
