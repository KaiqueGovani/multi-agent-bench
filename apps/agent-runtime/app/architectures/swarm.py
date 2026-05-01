"""Decentralized swarm architecture.

Agents collaborate peer-to-peer through a handoff loop.  A coordinator
starts the chain, specialist agents process in sequence, and a
synthesizer composes the final response.
"""

from __future__ import annotations

from app.architectures import register
from app.architectures.base import ExecutionContext, ExecutionResult
from app.architectures.centralized import _detect_review_required_in_text, _infer_route_from_tools


@register("decentralized_swarm")
class SwarmExecutor:
    """Decentralized swarm: peer-to-peer agent collaboration via handoff loop."""

    def execute(self, ctx: ExecutionContext) -> ExecutionResult:
        text = ctx.request.latest_message.content_text or ""

        if ctx.settings.enable_live_llm:
            return self._execute_live(ctx, text)

        return self._execute_mock(ctx, text)

    def _execute_live(self, ctx: ExecutionContext, text: str) -> ExecutionResult:
        from app.tools.domain_tools import faq_lookup, stock_lookup, attachment_intake

        system_prompt = (
            "Você faz parte de um swarm descentralizado de atendimento de farmácia. "
            "Colabore usando as ferramentas disponíveis (faq_lookup, stock_lookup, "
            "ou attachment_intake) e sintetize a resposta final em português do Brasil, "
            "em prosa corrida. Se a pergunta for clínica, recomende consultar um "
            "farmacêutico ou médico."
        )

        ctx.emit_reasoning(
            "swarm_synthesizer",
            "swarm.dispatch",
            "Swarm LLM ativo — colaboração descentralizada via Strands.",
            "live_llm",
            ["faq_lookup", "stock_lookup", "attachment_intake"],
        )

        result = ctx.invoke_live_supervisor(
            system_prompt=system_prompt,
            user_message=text,
            tools=[faq_lookup, stock_lookup, attachment_intake],
            supervisor_actor="swarm_synthesizer",
        )

        if result is None:
            return self._execute_mock(ctx, text)

        final_text, tool_calls = result
        route = _infer_route_from_tools(tool_calls)
        review_required = _detect_review_required_in_text(final_text)

        ctx.emit_final(
            final_text,
            route=route,
            final_actor="swarm_synthesizer",
            architecture_mode="decentralized_swarm",
            review_required=review_required,
        )
        ctx.emit("run", "completed", "completed",
                 payload={"phase": "completed", "reviewRequired": review_required})
        return ctx.build_result(final_text, review_required)

    def _execute_mock(self, ctx: ExecutionContext, text: str) -> ExecutionResult:
        route = "faq"
        specialist_actor = "faq_agent"

        # Handoff chain: coordinator → specialist → synthesizer
        chain = ["swarm_coordinator", specialist_actor, "swarm_synthesizer"]

        specialist_result: dict = {}
        for index, actor_name in enumerate(chain):
            node_id = f"swarm.{index}.{actor_name}"
            ctx.emit("node", "started", "running", actor_name=actor_name, node_id=node_id, payload={"stage": "handoff_loop", "position": index})

            if index == 0:
                ctx.emit_reasoning(
                    "swarm_coordinator", "swarm.coordinator.reasoning",
                    thought="Modo mock — sem classificação real.",
                    decision=route, candidates=["faq"],
                )
            if index > 0:
                ctx.loop_count += 1
                ctx.emit(
                    "handoff", "requested", "running",
                    actor_name=chain[index - 1],
                    node_id=f"swarm.handoff.{index}",
                    payload={"from": chain[index - 1], "to": actor_name, "hop": index},
                )
            if actor_name == specialist_actor:
                specialist_result = ctx.run_specialist(actor_name, phase="swarm")
                ctx.emit_message(
                    actor_name, f"swarm.{index}.{actor_name}.message",
                    "Especialista analisou a solicitação em modo mock.",
                )

            ctx.emit("node", "completed", "completed", actor_name=actor_name, node_id=node_id, payload={"stage": "handoff_loop", "position": index})

        # Compose and emit final response
        final_text = ctx.compose_response(
            architecture="decentralized_swarm",
            route=route,
            specialist_result=specialist_result,
            review_required=False,
        )
        ctx.emit_final(
            final_text,
            route=route,
            final_actor="swarm_synthesizer",
            architecture_mode="decentralized_swarm",
            review_required=False,
        )
        ctx.emit("run", "completed", "completed", payload={"phase": "completed", "reviewRequired": False})
        return ctx.build_result(final_text, False)
