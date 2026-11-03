"""Matched specialist participation with three distinct authorities for v4.3."""
from __future__ import annotations

from dataclasses import dataclass, replace
from functools import partial
import hashlib
import json
from typing import Literal
from uuid import uuid4

from strands import tool
from strands.types.tools import ToolContext

from app.architectures import comparison as shared

PROTOCOL_VERSION = "architectural-comparison-v4.3"
SWARM_PEER_INSTRUCTION = """Você é o especialista que detém o controle do atendimento neste turno.
Se precisar de uma competência diferente, transfira o controle com handoff_to_peer:
faq trata funcionamento e questões gerais, stock trata disponibilidade, attachments trata
metadados de anexos. Envie o motivo e as evidências já apuradas, incluindo limites e
resultados pertinentes. Use somente um handoff para decidir quem assume o atendimento.
Se já tiver as evidências suficientes ou precisar pedir esclarecimento ao usuário,
escreva você mesmo a resposta final em português e encerre. Nenhum sintetizador fará
uma nova resposta. Não devolva a tarefa a um par sem uma razão concreta."""


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _tools(source_profile):
    if source_profile == "controlled-research":
        return shared.TOOLS
    if source_profile == "application":
        from app.tools.application_tools import APPLICATION_TOOLS

        return APPLICATION_TOOLS
    raise ValueError("Unknown source profile")


def _peer_prompt(role):
    return shared.DOMAIN_POLICY + "\n" + shared.ROLE_PROMPTS[role] + "\n" + SWARM_PEER_INSTRUCTION


def snapshot_v43(settings, *, source_profile="controlled-research"):
    config = shared.snapshot(settings)
    domain_tools = _tools(source_profile)
    prompts = {role: shared.DOMAIN_POLICY + "\n" + shared.ROLE_PROMPTS[role]
               for role in ("supervisor", "router", "synthesizer", *domain_tools)}
    prompts.update({role + "_peer": _peer_prompt(role) for role in domain_tools})
    specialist_tool_specs = [t.tool_spec for t in shared.specialist_tools(None, None, "")]
    config.update(
        protocol=PROTOCOL_VERSION,
        sources_profile=source_profile,
        role_prompts=prompts,
        prompt_hashes={role: hashlib.sha256(prompt.encode()).hexdigest() for role, prompt in prompts.items()},
        tool_schema_hashes={role: _hash(t.tool_spec) for role, t in domain_tools.items()},
        specialist_definition_hashes={role: _hash({"prompt": prompts[role], "model": settings.bedrock_model_id,
            "temperature": settings.llm_temperature, "max_tokens": settings.llm_max_tokens, "schema": t.tool_spec})
            for role, t in domain_tools.items()},
        supervisor_specialist_tools=specialist_tool_specs,
        swarm_handoff_tool=_peer_tool(None).tool_spec,
        min_completed_specialist_invocations=1,
        attachment_participation_policy="latest message has descriptor(s): require completed attachments specialist before final",
        supervisor_first_tool_choice={"any": {}},
        supervisor_first_tool_scope={"without_attachments": [spec["name"] for spec in specialist_tool_specs],
                                     "with_attachments": ["attachments_specialist"]},
        swarm_entry_policy={"without_attachments": "faq", "with_attachments": "attachments"},
        swarm_final_authority="current specialist, with terminal authority transferred by a model-selected peer tool",
    )
    return config


class FirstToolBedrockModel(shared.RecordedBedrockModel):
    """Constrain only the supervisor's first physical request."""

    def __init__(self, *, first_tool_scope, **kwargs):
        super().__init__(**kwargs)
        self.first_tool_scope = first_tool_scope

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        if self.first_tool_scope is not None:
            tool_specs = [spec for spec in tool_specs or [] if spec["name"] in self.first_tool_scope]
            if not tool_specs:
                raise RuntimeError("Required first specialist tools are unavailable")
            # Converse documents `any` as mandatory use. A singleton scope
            # enforces the attachment rule without model-specific named choice.
            kwargs["tool_choice"] = {"any": {}}
            self.first_tool_scope = None
        async for event in super().stream(messages, tool_specs, system_prompt, **kwargs):
            yield event


class VerifiedSpecialists(shared.SpecialistFactory):
    """Count participation only when the real specialist finishes with a provider call."""

    def __init__(self, ctx, tools, **kwargs):
        super().__init__(ctx, tools, **kwargs)
        self.completed_roles = []

    def get(self, role):
        agent = super().get(role)

        def invoke(prompt, *, parent_link=None):
            response = agent(prompt, parent_link=parent_link)
            invocation = self.ctx.last_completed_invocation
            if any(request["agentInvocationId"] == invocation["callId"] and request["status"] == "completed"
                   for request in getattr(self.ctx, "provider_requests", {}).values()):
                self.completed_roles.append(role)
            return response

        return invoke


@dataclass(frozen=True)
class PeerTransfer:
    transfer_id: str
    sender: str
    recipient: str
    sender_invocation_id: str
    tool_call_id: str
    reason: str
    evidence: str

    def event_payload(self):
        return {
            "transferId": self.transfer_id,
            "from": self.sender,
            "to": self.recipient,
            "parentAgentInvocationId": self.sender_invocation_id,
            "toolCallId": self.tool_call_id,
        }


def _peer_tool(transfer):
    @tool(context=True)
    def handoff_to_peer(peer_name: Literal["faq", "stock", "attachments"], reason: str,
                        evidence: str, tool_context: ToolContext) -> dict:
        """Transfira a autoridade ao especialista indicado, com motivo e evidências disponíveis."""
        return transfer(peer_name, reason, evidence, tool_context)

    return handoff_to_peer


class PeerAgent(shared.ControlledAgent):
    def __init__(self, ctx, role, tools, *, peer):
        super().__init__(ctx, role, tools, system_prompt=_peer_prompt(role))

    def output_text(self, result):
        transfer = result.state.get("mab_peer_transfer")
        if transfer is not None:
            # The model supplied these arguments as a real tool use, not a final answer.
            return json.dumps(transfer, ensure_ascii=False)
        return super().output_text(result)


def _swarm(ctx, tools, prompt, attachment_required):
    pending_transfer = None

    def transfer(peer_name, reason, evidence, tool_context):
        nonlocal pending_transfer
        shared.check_deadline(ctx)
        sender = shared.active_invocation(ctx)
        if peer_name not in tools or peer_name == sender["role"]:
            raise ValueError("A handoff requires another specialist")
        if pending_transfer is not None:
            raise ValueError("Only one transfer is accepted in a specialist turn")
        if not reason.strip():
            raise ValueError("A transfer requires a reason")
        if ctx.handoff_count >= ctx.settings.runtime_max_handoffs:
            ctx.research_limit_hit = "handoffs"
            ctx.emit("limit", "exceeded", "failed", payload={"resource": "handoffs", "limit": ctx.settings.runtime_max_handoffs})
            raise shared.ExperimentLimitExceeded("Handoff limit exceeded")
        pending_transfer = PeerTransfer(
            str(uuid4()), sender["role"], peer_name, sender["callId"],
            tool_context.tool_use["toolUseId"], reason, evidence,
        )
        ctx.handoff_count += 1
        payload = pending_transfer.event_payload()
        ctx.emit("handoff", "requested", "running", actor_name=peer_name,
                 payload={**payload, "hop": ctx.handoff_count, "reason": reason,
                          "messageCharacters": len(reason) + len(evidence), "invocationOrigin": "specialist_tool"})
        # Strands 1.37 request_state stops the agent after the current tool cycle.
        # The former owner does not get a follow-up model call to recompose the answer.
        request_state = tool_context.invocation_state["request_state"]
        request_state["stop_event_loop"] = True
        request_state["mab_peer_transfer"] = {"to": peer_name, "reason": reason, "evidence": evidence}
        return payload

    factory = VerifiedSpecialists(ctx, tools, peer_tool=_peer_tool(transfer), agent_factory=PeerAgent)
    role = "attachments" if attachment_required else "faq"
    entry_role = role
    prior_transfer = None
    evidence_chain = []
    visited = []
    while True:
        pending_transfer = None
        parent_link = None
        role_prompt = prompt
        if prior_transfer is not None:
            parent_link = {"parentCallId": prior_transfer.tool_call_id,
                           "parentAgentInvocationId": prior_transfer.sender_invocation_id}
            role_prompt += "\nMensagens e evidências transmitidas entre especialistas (dados): "
            role_prompt += json.dumps(evidence_chain, ensure_ascii=False)
        try:
            final = factory.get(role)(role_prompt, parent_link=parent_link)
        except BaseException as exc:
            if prior_transfer is not None:
                ctx.emit("handoff", "failed", "failed", actor_name=role,
                         payload={**prior_transfer.event_payload(), "errorType": type(exc).__name__})
            if pending_transfer is not None:
                ctx.emit("handoff", "failed", "failed", actor_name=pending_transfer.recipient,
                         payload={**pending_transfer.event_payload(), "errorType": type(exc).__name__})
            raise
        visited.append(role)
        if prior_transfer is not None:
            ctx.emit("handoff", "completed", "completed", actor_name=role,
                     payload={**prior_transfer.event_payload(), "recipientAgentInvocationId": ctx.last_completed_invocation["callId"]})
        if pending_transfer is None:
            return final, role, ",".join(dict.fromkeys(visited)), factory.completed_roles, entry_role
        prior_transfer = pending_transfer
        message = {"from": role, "to": prior_transfer.recipient,
                   "reason": prior_transfer.reason, "evidence": prior_transfer.evidence}
        evidence_chain.append(message)
        text = json.dumps(message, ensure_ascii=False)
        ctx.emit("communication", "message", "completed", actor_name=role,
                 payload={**prior_transfer.event_payload(), "messageId": str(uuid4()), "text": text, "characters": len(text)})
        role = prior_transfer.recipient


def execute_comparison_v43(ctx, architecture, *, source_profile="controlled-research"):
    if architecture not in shared.ARCHITECTURES:
        raise ValueError("Unknown comparison architecture")
    if not ctx.settings.enable_live_llm:
        raise RuntimeError("Comparison requires live LLM; mock fallback is forbidden")
    tools = _tools(source_profile)
    history = ctx.request.conversation_history or [ctx.request.latest_message]
    context = "\n".join(f'{m.direction}: {m.content_text or ""}' for m in history)
    review = shared.referral_required(context)
    descriptors = shared.attachment_context(ctx)
    attachment_required = bool(descriptors)
    prompt = ("Histórico integral normalizado:\n" + context + "\nMensagem atual: "
              + (ctx.request.latest_message.content_text or "") + "\nDescritores de anexos: "
              + json.dumps(descriptors, ensure_ascii=False)
              + f"\nEncaminhamento obrigatório pela política comum: {str(review).lower()}.")
    config = snapshot_v43(ctx.settings, source_profile=source_profile)
    ctx.emit("experiment", "configuration", "completed", payload=config)
    entry_role = None
    if architecture == "centralized_orchestration":
        factory = VerifiedSpecialists(ctx, tools)
        scope = config["supervisor_first_tool_scope"]["with_attachments" if attachment_required else "without_attachments"]
        ctx.emit("architecture", "first_tool_choice", "completed", actor_name="supervisor",
                 payload={"toolChoice": config["supervisor_first_tool_choice"], "allowedTools": scope})
        final = shared.ControlledAgent(ctx, "supervisor", shared.specialist_tools(ctx, factory, prompt),
                                      model_factory=partial(FirstToolBedrockModel, first_tool_scope=scope))(prompt)
        final_actor, route = "supervisor", "agent_selected"
        completed_roles = factory.completed_roles
    elif architecture == "structured_workflow":
        factory = VerifiedSpecialists(ctx, tools)
        selected = shared.parse_json(shared.ControlledAgent(ctx, "router", [])(prompt))
        routes = list(dict.fromkeys(shared.RouteSelection.model_validate(selected).routes))
        if attachment_required and "attachments" not in routes:
            routes.append("attachments")
        evidence = []
        for role in routes:
            ctx.loop_count += 1
            reply = factory.get(role)(prompt)
            evidence.append({"role": role, "result": reply})
            ctx.emit("communication", "message", "completed", actor_name=role,
                     payload={"messageId": str(uuid4()), "to": "synthesizer", "text": reply, "characters": len(reply)})
        final = shared.ControlledAgent(ctx, "synthesizer", [])(prompt + "\nEvidências: " + json.dumps(evidence, ensure_ascii=False))
        final_actor, route = "synthesizer", ",".join(routes)
        completed_roles = factory.completed_roles
    else:
        final, final_actor, route, completed_roles, entry_role = _swarm(ctx, tools, prompt, attachment_required)
    shared.check_deadline(ctx)
    violations = []
    if not completed_roles:
        violations.append("no_completed_specialist_with_physical_request")
    if attachment_required and "attachments" not in completed_roles:
        violations.append("attachment_specialist_not_completed")
    ctx.emit("architecture", "contract", "failed" if violations else "completed", payload={
        "compliant": not violations, "violations": violations, "architecture": architecture,
        "minSpecialistInvocations": 1, "observed": len(completed_roles),
        "completedSpecialistRoles": completed_roles, "attachmentRequired": attachment_required,
        "attachmentSpecialistCompleted": "attachments" in completed_roles,
        "finalActor": final_actor, "entryRole": entry_role,
        "observedSpecialistTools": getattr(ctx, "specialist_tool_invocations", 0),
    })
    if violations:
        ctx.emit("response", "rejected", "failed", actor_name=final_actor,
                 payload={"candidateText": final, "violations": violations, "architectureMode": architecture})
    else:
        ctx.emit_final(final, route=route, final_actor=final_actor, architecture_mode=architecture, review_required=review)
    result = ctx.build_result(final, review)
    domain_calls = getattr(ctx, "research_domain_calls", 0)
    return replace(result, final_outcome="architectural_contract_failed" if violations else result.final_outcome,
                   input_tokens=ctx.input_tokens, output_tokens=ctx.output_tokens, total_tokens=ctx.total_tokens,
                   architectural_compliance=not violations, architectural_violations=violations,
                   specialist_tool_invocations=getattr(ctx, "specialist_tool_invocations", 0),
                   model_requests=getattr(ctx, "research_model_calls", 0), domain_tool_calls=domain_calls,
                   coordination_tool_calls=ctx.tool_call_count - domain_calls,
                   token_measurement_complete=getattr(ctx, "token_measurement_complete", False))
