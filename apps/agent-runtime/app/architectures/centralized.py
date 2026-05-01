"""Centralized orchestration architecture.

A single supervisor agent classifies the inbound message, routes to the
appropriate specialist, applies a review gate, and composes the final
response.  All decisions flow through the supervisor.
"""

from __future__ import annotations

from app.architectures import register
from app.architectures.base import ExecutionContext, ExecutionResult


def _infer_route_from_tools(tool_calls: list[dict]) -> str:
    """Map the first used tool to our route enum."""
    if not tool_calls:
        return "faq"
    name_to_route = {
        "faq_lookup": "faq",
        "stock_lookup": "stock_lookup",
        "attachment_intake": "image_intake",
    }
    return name_to_route.get(tool_calls[0]["name"], "faq")


def _detect_review_required_in_text(text: str) -> bool:
    """The LLM is instructed to recommend a pharmacist; flag when it does."""
    lower = text.lower()
    return any(kw in lower for kw in ["farmacêutico", "farmaceutico", "médico", "medico", "consulte um profissional"])


@register("centralized_orchestration")
class CentralizedExecutor:
    """Centralized orchestration: supervisor classifies, routes, and composes."""

    def execute(self, ctx: ExecutionContext) -> ExecutionResult:
        text = ctx.request.latest_message.content_text or ""

        if ctx.settings.enable_live_llm:
            return self._execute_live(ctx, text)

        return self._execute_mock(ctx, text)

    def _execute_live(self, ctx: ExecutionContext, text: str) -> ExecutionResult:
        from app.tools.domain_tools import faq_lookup, stock_lookup, attachment_intake

        system_prompt = (
            "Você é um supervisor de atendimento de uma farmácia. Dado a mensagem do usuário, "
            "você decide qual ferramenta usar (faq_lookup, stock_lookup, ou attachment_intake) "
            "e compoe a resposta final em português do Brasil, em prosa corrida. "
            "Se a pergunta for clínica (dosagem, interação, efeito colateral, gestação), sempre "
            "recomende consultar um farmacêutico ou médico. Nunca forneça dosagens específicas. "
            "Se o usuário enviou anexos, use attachment_intake primeiro."
        )

        ctx.emit_reasoning(
            "supervisor_agent",
            "supervisor.dispatch",
            "Supervisor LLM ativo — decide rota e ferramenta via Strands.",
            "live_llm",
            ["faq_lookup", "stock_lookup", "attachment_intake"],
        )

        result = ctx.invoke_live_supervisor(
            system_prompt=system_prompt,
            user_message=text,
            tools=[faq_lookup, stock_lookup, attachment_intake],
        )

        if result is None:
            return self._execute_mock(ctx, text)

        final_text, tool_calls = result
        route = _infer_route_from_tools(tool_calls)
        review_required = _detect_review_required_in_text(final_text)

        ctx.emit_final(
            final_text,
            route=route,
            final_actor="supervisor_agent",
            architecture_mode="centralized_orchestration",
            review_required=review_required,
        )
        ctx.emit("run", "completed", "completed",
                 payload={"phase": "completed", "reviewRequired": review_required})
        return ctx.build_result(final_text, review_required)

    def _execute_mock(self, ctx: ExecutionContext, text: str) -> ExecutionResult:
        route = "faq"
        specialist_actor = "faq_agent"

        # Supervisor reasoning (trivial in mock mode)
        ctx.emit_reasoning(
            "supervisor_agent", "supervisor.classify.reasoning",
            thought="Modo mock — sem classificação real.",
            decision=route, candidates=["faq"],
        )

        # Handoff to specialist
        ctx.emit(
            "handoff", "requested", "running",
            actor_name="supervisor_agent",
            node_id="handoff.specialist",
            payload={"route": route, "targetActor": specialist_actor},
        )

        result = ctx.run_specialist(specialist_actor, phase="specialist")

        # Compose and emit final response
        final_text = ctx.compose_response(
            architecture="centralized_orchestration",
            route=route,
            specialist_result=result,
            review_required=False,
        )
        ctx.emit_final(
            final_text,
            route=route,
            final_actor="supervisor_agent",
            architecture_mode="centralized_orchestration",
            review_required=False,
        )
        ctx.emit(
            "run", "completed", "completed",
            payload={"phase": "completed", "reviewRequired": False},
        )
        return ctx.build_result(final_text, False)
