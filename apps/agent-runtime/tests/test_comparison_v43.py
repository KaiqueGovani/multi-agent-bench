"""Exercise real Strands 1.37 agents with a controlled Converse transport."""
from collections import deque
from dataclasses import replace
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from strands.models.bedrock import BedrockModel

from app.architectures import comparison as v42
from app.architectures import comparison_v43 as v43
from app.schemas.runtime import RuntimeAttachmentDescriptor
from test_research_comparison import context


def provider(monkeypatch, *steps):
    script = deque(steps)
    requests = []

    def init(model, **kwargs):
        model.config = {k: v for k, v in kwargs.items() if k not in {"boto_client_config", "region_name"}}
        model.config["include_tool_result_status"] = "auto"
        model.client = SimpleNamespace(converse=lambda **request: converse(model, request))

    def converse(model, request):
        requests.append((model.role, request))
        role, content = script.popleft()
        assert model.role == role
        if callable(content):
            content = content(request)
        if isinstance(content, str):
            content = [{"text": content}]
        return {
            "output": {"message": {"role": "assistant", "content": content}},
            "stopReason": "tool_use" if any("toolUse" in block for block in content) else "end_turn",
            "usage": {"inputTokens": 7, "outputTokens": 3, "totalTokens": 10},
            "metrics": {"latencyMs": 1},
        }

    monkeypatch.setattr(BedrockModel, "__init__", init)
    return requests, script


def tool_use(name, tool_call_id, **arguments):
    return [{"toolUse": {"toolUseId": tool_call_id, "name": name, "input": arguments}}]


def attach(ctx):
    message = ctx.request.latest_message
    message.attachments = [RuntimeAttachmentDescriptor(
        attachment_id=uuid4(), message_id=message.id, original_filename="foto.png",
        mime_type="image/png", size_bytes=20, checksum="synthetic", retrieval_url="http://private.invalid/not-in-prompt",
    )]


def event(ctx, family, name):
    return next(e for e in ctx.callbacks.events if e.event_family == family and e.event_name == name)


def test_supervisor_first_use_any_then_supervisor_retains_authority(monkeypatch):
    requests, script = provider(monkeypatch,
        ("supervisor", tool_use("stock_specialist", "delegate", task="estoque")),
        ("stock", tool_use("stock_lookup", "source", question="dipirona")),
        ("stock", "Evidência do especialista"),
        ("supervisor", "Resposta final do supervisor"),
    )
    ctx = context("centralized_orchestration", "Tem dipirona?")
    result = v43.execute_comparison_v43(ctx, "centralized_orchestration")
    assert not script
    assert requests[0][1]["toolConfig"]["toolChoice"] == {"any": {}}
    assert {t["toolSpec"]["name"] for t in requests[0][1]["toolConfig"]["tools"]} == v42.SPECIALIST_NAMES
    assert requests[-1][1]["toolConfig"]["toolChoice"] == {"auto": {}}
    tool_result = requests[-1][1]["messages"][-1]["content"][0]["toolResult"]
    assert json.loads(tool_result["content"][0]["text"])["result"] == "Evidência do especialista"
    assert event(ctx, "response", "final").actor_name == "supervisor"
    assert result.architectural_compliance and result.total_tokens == 40
    assert result.specialist_tool_invocations == 1 and result.domain_tool_calls == 1


@pytest.mark.parametrize("architecture", v42.ARCHITECTURES)
def test_all_architectures_require_attachment_participation(monkeypatch, architecture):
    def route(request):
        tool_name = request["toolConfig"]["tools"][-1]["toolSpec"]["name"]
        return tool_use(tool_name, "route", routes=["faq"])

    scripts = {
        "centralized_orchestration": (("supervisor", tool_use("attachments_specialist", "delegate", task="anexo")),
                                      ("attachments", "Metadados"), ("supervisor", "Resposta")),
        "structured_workflow": (("router", route), ("faq", "Evidência"), ("attachments", "Metadados"),
                                ("synthesizer", "Resposta")),
        "decentralized_swarm": (("attachments", "Resposta"),),
    }
    requests, script = provider(monkeypatch, *scripts[architecture])
    ctx = context(architecture, "Considere o arquivo")
    attach(ctx)
    result = v43.execute_comparison_v43(ctx, architecture)
    assert not script
    assert result.architectural_compliance
    contract = event(ctx, "architecture", "contract")
    assert contract.payload["attachmentRequired"] and contract.payload["attachmentSpecialistCompleted"]
    assert "attachments" in contract.payload["completedSpecialistRoles"]
    assert all("private.invalid" not in str(request["messages"]) for _, request in requests)
    if architecture == "centralized_orchestration":
        assert requests[0][1]["toolConfig"]["toolChoice"] == {"any": {}}
        assert [t["toolSpec"]["name"] for t in requests[0][1]["toolConfig"]["tools"]] == ["attachments_specialist"]
        assert {t["toolSpec"]["name"] for t in requests[-1][1]["toolConfig"]["tools"]} == v42.SPECIALIST_NAMES
    if architecture == "decentralized_swarm":
        assert event(ctx, "response", "final").actor_name == "attachments"


@pytest.mark.parametrize("with_attachment", [False, True])
def test_provider_ignoring_first_tool_choice_cannot_release_answer(monkeypatch, with_attachment):
    requests, script = provider(monkeypatch, ("supervisor", "Candidato sem delegação"))
    ctx = context("centralized_orchestration")
    if with_attachment:
        attach(ctx)
    result = v43.execute_comparison_v43(ctx, "centralized_orchestration")
    assert len(requests) == 1 and not script
    assert result.final_outcome == "architectural_contract_failed"
    assert result.final_text == "Candidato sem delegação"
    assert not result.architectural_compliance
    assert result.architectural_violations == ["no_completed_specialist_with_physical_request"] + (
        ["attachment_specialist_not_completed"] if with_attachment else [])
    assert event(ctx, "response", "rejected").status == "failed"
    assert not any(e.event_family == "response" and e.event_name == "final" for e in ctx.callbacks.events)


def test_swarm_handoff_transfers_final_authority_without_reentering_sender(monkeypatch):
    requests, script = provider(monkeypatch,
        ("faq", tool_use("faq_lookup", "faq-source", question="horário")),
        ("faq", tool_use("handoff_to_peer", "handoff", peer_name="stock", reason="consultar disponibilidade",
                         evidence="FAQ informou 8h–22h")),
        ("stock", tool_use("stock_lookup", "stock-source", question="dipirona")),
        ("stock", "Resposta do especialista: há dipirona e atendemos até 22h."),
    )
    ctx = context("decentralized_swarm", "Tem dipirona e até que horas funciona?")
    result = v43.execute_comparison_v43(ctx, "decentralized_swarm")
    assert not script
    assert [role for role, _ in requests] == ["faq", "faq", "stock", "stock"]
    assert "FAQ informou 8h–22h" in str(requests[2][1]["messages"])
    assert "Tem dipirona e até que horas funciona?" in str(requests[2][1]["messages"])
    assert event(ctx, "response", "final").actor_name == "stock"
    assert result.final_text.startswith("Resposta do especialista")
    assert result.handoff_count == 1 and result.model_requests == 4 and result.total_tokens == 40
    request_event = event(ctx, "handoff", "requested")
    assert request_event.payload["from"] == "faq" and request_event.payload["to"] == "stock"
    assert request_event.payload["invocationOrigin"] == "specialist_tool"
    starts = [e for e in ctx.callbacks.events if e.event_family == "agent" and e.event_name == "started"]
    assert starts[1].payload["parentAgentInvocationId"] == starts[0].payload["callId"]
    assert starts[1].payload["parentCallId"] == request_event.payload["toolCallId"]
    assert event(ctx, "handoff", "completed").payload["recipientAgentInvocationId"] == starts[1].payload["callId"]


def test_swarm_global_limit_prevents_next_transfer(monkeypatch):
    requests, script = provider(monkeypatch,
        ("faq", tool_use("handoff_to_peer", "first", peer_name="stock", reason="estoque", evidence="")),
        ("stock", tool_use("handoff_to_peer", "second", peer_name="attachments", reason="anexo", evidence="")),
    )
    ctx = context("decentralized_swarm")
    ctx.settings = replace(ctx.settings, runtime_max_handoffs=1)
    with pytest.raises(v42.ExperimentLimitExceeded, match="handoffs"):
        v43.execute_comparison_v43(ctx, "decentralized_swarm")
    assert not script and len(requests) == 2
    assert ctx.handoff_count == 1 and not ctx.invocation_stack
    assert event(ctx, "limit", "exceeded").payload["resource"] == "handoffs"


def test_peer_revisit_keeps_its_state_only_within_one_attempt(monkeypatch):
    requests, script = provider(monkeypatch,
        ("faq", tool_use("handoff_to_peer", "first", peer_name="stock", reason="estoque", evidence="")),
        ("stock", tool_use("handoff_to_peer", "second", peer_name="faq", reason="combinar", evidence="17 unidades")),
        ("faq", "Resposta integrada"),
        ("faq", "Resposta de outra tentativa"),
    )
    first = context("decentralized_swarm", "Contexto sintético da primeira tentativa")
    second = context("decentralized_swarm", "Contexto sintético independente")
    assert v43.execute_comparison_v43(first, "decentralized_swarm").handoff_count == 2
    assert v43.execute_comparison_v43(second, "decentralized_swarm").handoff_count == 0
    assert not script
    first_starts = [e.payload for e in first.callbacks.events if e.event_family == "agent" and e.event_name == "started"]
    second_start = event(second, "agent", "started").payload
    assert first_starts[0]["agentId"] == first_starts[2]["agentId"]
    assert first_starts[0]["callId"] != first_starts[2]["callId"]
    assert second_start["agentId"] != first_starts[0]["agentId"]
    assert "17 unidades" in str(requests[2][1]["messages"])
    assert "primeira tentativa" not in str(requests[3][1]["messages"])
    assert "17 unidades" not in str(requests[3][1]["messages"])
