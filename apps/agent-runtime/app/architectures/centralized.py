"""Centralized orchestration architecture.

A single supervisor agent classifies the inbound message, routes to the
appropriate specialist, applies a review gate, and composes the final
response.  All decisions flow through the supervisor.
"""

from __future__ import annotations

from app.architectures import register
from app.architectures.base import ExecutionContext, ExecutionResult
from app.tools.domain_tools import infer_route, request_human_review, should_request_review


@register("centralized_orchestration")
class CentralizedExecutor:
    """Centralized orchestration: a supervisor agent classifies, routes to a
    specialist, applies review gate, and composes the response."""

    def execute(self, ctx: ExecutionContext) -> ExecutionResult:
        text = ctx.request.latest_message.content_text or ""
        route = infer_route(text, ctx.attachment_dicts())
        specialist_actor = ctx.specialist_actor(route)

        # Supervisor classifies the message
        ctx.emit(
            "node",
            "started",
            "running",
            actor_name="supervisor_agent",
            node_id="supervisor.classify",
            payload={"phase": "routing", "text": text, "route": route},
        )
        ctx.emit(
            "node",
            "completed",
            "completed",
            actor_name="supervisor_agent",
            node_id="supervisor.classify",
            payload={"route": route},
        )

        # Handoff to specialist
        ctx.emit(
            "handoff",
            "requested",
            "running",
            actor_name="supervisor_agent",
            node_id="handoff.specialist",
            payload={"route": route, "targetActor": specialist_actor},
        )

        specialist_result = ctx.run_specialist(specialist_actor, phase="specialist")

        # Review gate
        review_required = should_request_review(text)
        if review_required:
            review_result = request_human_review("Content requires human review by policy.")
            ctx.emit(
                "review",
                "required",
                "human_review_required",
                actor_name="supervisor_agent",
                node_id="supervisor.review_gate",
                payload=review_result,
            )

        # Compose and emit final response
        final_text = ctx.compose_response(
            architecture="centralized_orchestration",
            route=route,
            specialist_result=specialist_result,
            review_required=review_required,
        )
        ctx.emit_partial(final_text)
        ctx.emit(
            "response",
            "final",
            "completed",
            actor_name="supervisor_agent",
            node_id="supervisor.respond",
            payload={"contentText": final_text, "reviewRequired": review_required},
        )
        ctx.emit(
            "run",
            "completed",
            "completed",
            payload={"phase": "completed", "reviewRequired": review_required},
        )
        return ctx.build_result(final_text, review_required)
