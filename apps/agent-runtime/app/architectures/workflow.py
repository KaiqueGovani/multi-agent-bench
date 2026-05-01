"""Structured workflow architecture.

A predefined pipeline of stages (classify → evidence → review →
synthesize) processes the message sequentially.  Each stage is handled
by a dedicated agent with a fixed responsibility.
"""

from __future__ import annotations

from app.architectures import register
from app.architectures.base import ExecutionContext, ExecutionResult
from app.architectures.centralized import _detect_review_required_in_text, _infer_route_from_tools


@register("structured_workflow")
class WorkflowExecutor:
    """Structured workflow: predefined pipeline stages with specialised agents."""

    def execute(self, ctx: ExecutionContext) -> ExecutionResult:
        text = ctx.request.latest_message.content_text or ""

        if ctx.settings.enable_live_llm:
            return self._execute_live(ctx, text)

        return self._execute_mock(ctx, text)

    def _execute_live(self, ctx: ExecutionContext, text: str) -> ExecutionResult:
        from app.tools.domain_tools import faq_lookup, stock_lookup, attachment_intake

        system_prompt = (
            "Você é um pipeline estruturado de atendimento de farmácia. "
            "Classifique a mensagem, colete evidências usando a ferramenta adequada "
            "(faq_lookup, stock_lookup, ou attachment_intake), revise e sintetize "
            "a resposta final em português do Brasil, em prosa corrida. "
            "Se a pergunta for clínica, recomende consultar um farmacêutico ou médico."
        )

        ctx.emit_reasoning(
            "workflow_synthesizer",
            "workflow.dispatch",
            "Workflow LLM ativo — pipeline estruturado via Strands.",
            "live_llm",
            ["faq_lookup", "stock_lookup", "attachment_intake"],
        )

        result = ctx.invoke_live_supervisor(
            system_prompt=system_prompt,
            user_message=text,
            tools=[faq_lookup, stock_lookup, attachment_intake],
            supervisor_actor="workflow_synthesizer",
        )

        if result is None:
            return self._execute_mock(ctx, text)

        final_text, tool_calls = result
        route = _infer_route_from_tools(tool_calls)
        review_required = _detect_review_required_in_text(final_text)

        ctx.emit_final(
            final_text,
            route=route,
            final_actor="workflow_synthesizer",
            architecture_mode="structured_workflow",
            review_required=review_required,
        )
        ctx.emit("run", "completed", "completed",
                 payload={"phase": "completed", "reviewRequired": review_required})
        return ctx.build_result(final_text, review_required)

    def _execute_mock(self, ctx: ExecutionContext, text: str) -> ExecutionResult:
        route = "faq"
        specialist_actor = "faq_agent"

        # Build the stage pipeline
        stages: list[tuple[str, str, dict]] = [
            ("workflow.classify", "router_agent", {"stage": "classify", "route": route}),
            ("workflow.evidence", "workflow_evidence_agent", {"stage": "gather_evidence"}),
            ("workflow.review", "workflow_review_agent", {"stage": "review_gate"}),
            ("workflow.synthesize", "workflow_synthesis_agent", {"stage": "synthesize"}),
        ]

        # Execute each stage in order
        specialist_result: dict = {}
        for node_id, actor_name, payload in stages:
            ctx.emit("node", "started", "running", actor_name=actor_name, node_id=node_id, payload=payload)
            if node_id == "workflow.classify":
                ctx.emit_reasoning(
                    "router_agent", "workflow.classify.reasoning",
                    thought="Modo mock — sem classificação real.",
                    decision=route, candidates=["faq"],
                )
            if node_id == "workflow.evidence":
                specialist_result = ctx.run_specialist(specialist_actor, phase="workflow")
            ctx.emit("node", "completed", "completed", actor_name=actor_name, node_id=node_id, payload=payload)

        # Compose and emit final response
        final_text = ctx.compose_response(
            architecture="structured_workflow",
            route=route,
            specialist_result=specialist_result,
            review_required=False,
        )
        ctx.emit_final(
            final_text,
            route=route,
            final_actor="workflow_synthesis_agent",
            architecture_mode="structured_workflow",
            review_required=False,
        )
        ctx.emit("run", "completed", "completed", payload={"phase": "completed", "reviewRequired": False})
        return ctx.build_result(final_text, False)
