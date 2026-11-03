"""Executor-enforced supervisor delegation with the v4.2 comparator branches."""
from __future__ import annotations

from dataclasses import replace
from functools import partial

from app.architectures import comparison as shared

PROTOCOL_VERSION = "architectural-comparison-v4.4"


def snapshot_v44(settings, *, source_profile="controlled-research"):
    config = shared.snapshot(settings)
    tools = [tool.tool_spec for tool in shared.specialist_tools(None, None, "")]
    config.update(
        protocol=PROTOCOL_VERSION,
        sources_profile=source_profile,
        supervisor_specialist_tools=tools,
        supervisor_first_tool_choice={"any": {}},
        supervisor_first_tool_scope={"without_attachments": [spec["name"] for spec in tools],
                                     "with_attachments": ["attachments_specialist"]},
        supervisor_tool_scope_enforcement="The model and executor share the scope for each supervisor turn. "
        "An out-of-scope request receives a tool error before execution. Follow-up tools are enabled on a subsequent "
        "supervisor turn after the mandatory real specialist completes.",
        attachment_participation_policy="Latest-message attachment metadata requires the attachments specialist before the final response.",
        workflow_and_swarm_core="architectural-comparison-v4.2",
    )
    return config


class SupervisorDelegation:
    """Keep the dispatch scope stable across every tool request in one model turn."""

    def __init__(self, ctx, config):
        self.ctx = ctx
        self.attachment_required = bool(ctx.request.latest_message.attachments)
        scopes = config["supervisor_first_tool_scope"]
        self.all_tools = scopes["without_attachments"]
        self.mandatory_tools = scopes["with_attachments"] if self.attachment_required else self.all_tools
        self.active_scope = self.mandatory_tools
        self.model_turn = 0
        self.completed_roles = []
        self.rejected_calls = set()
        self.rejection_count = 0

    @property
    def mandatory_completed(self):
        return "attachments" in self.completed_roles if self.attachment_required else bool(self.completed_roles)

    def note_completed(self, role):
        invocation = self.ctx.last_completed_invocation
        physical_requests = getattr(self.ctx, "provider_requests", {})
        if invocation["role"] == role and any(
            call["agentInvocationId"] == invocation["callId"] and call["status"] == "completed"
            for call in physical_requests.values()
        ):
            self.completed_roles.append(role)

    def begin_model_turn(self):
        shared.check_deadline(self.ctx)
        self.model_turn += 1
        mandatory_completed = self.mandatory_completed
        self.active_scope = self.all_tools if mandatory_completed else self.mandatory_tools
        choice = {"auto": {}} if mandatory_completed else {"any": {}}
        self.ctx.emit("architecture", "tool_scope", "completed", actor_name="supervisor", payload={
            "supervisorModelTurn": self.model_turn, "toolChoice": choice,
            "allowedTools": self.active_scope, "mandatorySpecialistCompleted": mandatory_completed,
        })
        return choice


class ScopedSupervisorModel(shared.RecordedBedrockModel):
    def __init__(self, *, delegation, **kwargs):
        super().__init__(**kwargs)
        self.delegation = delegation

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        kwargs["tool_choice"] = self.delegation.begin_model_turn()
        available = [spec for spec in tool_specs or [] if spec["name"] in self.delegation.active_scope]
        if {spec["name"] for spec in available} != set(self.delegation.active_scope):
            raise RuntimeError("Supervisor specialist tool registry does not match the required scope")
        async for event in super().stream(messages, available, system_prompt, **kwargs):
            yield event


class ScopedSupervisorTools(shared.ToolEvents):
    def __init__(self, ctx, delegation):
        super().__init__(ctx, "supervisor")
        self.delegation = delegation

    def before(self, event):
        shared.check_deadline(self.ctx)
        use = event.tool_use
        name = use["name"]
        if name in self.delegation.active_scope:
            super().before(event)
            return
        tool_call_id = use["toolUseId"]
        self.delegation.rejected_calls.add(tool_call_id)
        self.delegation.rejection_count += 1
        event.cancel_tool = "Ferramenta fora do escopo deste turno. Consulte as ferramentas disponíveis neste turno."
        invocation = shared.active_invocation(self.ctx)
        self.ctx.emit("tool", "rejected", "failed", actor_name=self.role, tool_name=name, payload={
            "toolCallId": tool_call_id, "agentInvocationId": invocation.get("callId"),
            "parentCallId": invocation.get("callId"), "agentId": invocation.get("agentId"),
            "supervisorModelTurn": self.delegation.model_turn,
            "allowedTools": self.delegation.active_scope, "reason": "outside_supervisor_turn_scope",
            "input": use.get("input", {}),
        })

    def after(self, event):
        tool_call_id = event.tool_use["toolUseId"]
        if tool_call_id in self.delegation.rejected_calls and event.cancel_message:
            # The SDK supplies an error result to the supervisor without running a child.
            self.delegation.rejected_calls.remove(tool_call_id)
            return
        super().after(event)


def _execute_supervisor(ctx, factory, prompt, review, config):
    delegation = SupervisorDelegation(ctx, config)
    tools = shared.specialist_tools(ctx, factory, prompt, on_completed=delegation.note_completed)
    final = shared.ControlledAgent(
        ctx, "supervisor", tools,
        model_factory=partial(ScopedSupervisorModel, delegation=delegation),
        tool_events=ScopedSupervisorTools(ctx, delegation),
    )(prompt)
    shared.check_deadline(ctx)
    if ctx.tool_error_count:
        ctx.emit("run", "warning", "completed", payload={"reason": "tool_errors_observed_final_response_available",
                                                           "toolErrorCount": ctx.tool_error_count})
    violations = []
    if not delegation.completed_roles:
        violations.append("no_completed_specialist_with_physical_request")
    if delegation.attachment_required and not delegation.mandatory_completed:
        violations.append("attachment_specialist_not_completed")
    architecture = "centralized_orchestration"
    invocation_count = getattr(ctx, "specialist_tool_invocations", 0)
    ctx.emit("architecture", "contract", "failed" if violations else "completed", payload={
        "architecture": architecture, "compliant": not violations, "violations": violations,
        "minSpecialistInvocations": 1, "maxSpecialistInvocations": shared.MAX_SPECIALIST_INVOCATIONS,
        "observed": len(delegation.completed_roles), "observedSpecialistTools": invocation_count,
        "completedSpecialistRoles": delegation.completed_roles, "attachmentRequired": delegation.attachment_required,
        "attachmentSpecialistCompleted": "attachments" in delegation.completed_roles,
        "scopeRejectedToolRequests": delegation.rejection_count, "finalActor": "supervisor",
    })
    if violations:
        ctx.emit("response", "rejected", "failed", actor_name="supervisor",
                 payload={"candidateText": final, "violations": violations, "architectureMode": architecture})
    else:
        ctx.emit_final(final, route="agent_selected", final_actor="supervisor", architecture_mode=architecture, review_required=review)
    result = ctx.build_result(final, review)
    domain_calls = getattr(ctx, "research_domain_calls", 0)
    return replace(result, final_outcome="architectural_contract_failed" if violations else result.final_outcome,
                   architectural_compliance=not violations, architectural_violations=violations,
                   input_tokens=ctx.input_tokens, output_tokens=ctx.output_tokens, total_tokens=ctx.total_tokens,
                   specialist_tool_invocations=invocation_count, model_requests=getattr(ctx, "research_model_calls", 0),
                   domain_tool_calls=domain_calls, coordination_tool_calls=ctx.tool_call_count - domain_calls,
                   token_measurement_complete=getattr(ctx, "token_measurement_complete", False))


def execute_comparison_v44(ctx, architecture, *, source_profile="controlled-research"):
    return shared.execute_comparison(
        ctx, architecture, source_profile=source_profile,
        configuration_factory=partial(snapshot_v44, source_profile=source_profile),
        central_executor=_execute_supervisor,
    )
