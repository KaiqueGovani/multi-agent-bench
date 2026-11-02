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
        from app.architectures.comparison import execute_comparison
        return execute_comparison(ctx, "centralized_orchestration", source_profile="application")

    def _execute_mock(self, ctx: ExecutionContext, text: str) -> ExecutionResult:
        route = ctx.infer_route_from_context()
        specialist_actor = ctx.specialist_actor(route)

        # Single supervisor reasoning — mirrors live pattern (no handoffs)
        ctx.emit_reasoning(
            "supervisor_agent", "supervisor.classify.reasoning",
            thought="Modo mock — sem classificação real.",
            decision=route, candidates=["faq"],
        )

        # Simulated tool call via run_specialist (emits tool.started/completed
        # and node.started/completed internally)
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
