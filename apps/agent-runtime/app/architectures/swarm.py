"""Decentralized swarm architecture.

Agents collaborate peer-to-peer through a handoff loop.  A coordinator
starts the chain, specialist agents process in sequence, and a
synthesizer composes the final response.
"""

from __future__ import annotations

from app.architectures import register
from app.architectures.base import ExecutionContext, ExecutionResult
from app.tools.domain_tools import infer_route, request_human_review, should_request_review


@register("decentralized_swarm")
class SwarmExecutor:
    """Decentralized swarm: peer-to-peer agent collaboration via handoff loop."""

    def execute(self, ctx: ExecutionContext) -> ExecutionResult:
        text = ctx.request.latest_message.content_text or ""
        route = infer_route(text, ctx.attachment_dicts())
        specialist_actor = ctx.specialist_actor(route)

        # Build the handoff chain
        chain = ["swarm_coordinator", specialist_actor]
        if specialist_actor != "faq_agent":
            chain.append("faq_agent")
        chain.append("swarm_synthesizer")

        # Execute the handoff loop
        specialist_result = None
        for index, actor_name in enumerate(chain):
            node_id = f"swarm.{index}.{actor_name}"
            ctx.emit("node", "started", "running", actor_name=actor_name, node_id=node_id, payload={"stage": "handoff_loop", "position": index})
            if index > 0:
                ctx.loop_count += 1
                ctx.emit(
                    "handoff",
                    "requested",
                    "running",
                    actor_name=chain[index - 1],
                    node_id=f"swarm.handoff.{index}",
                    payload={"from": chain[index - 1], "to": actor_name, "hop": index},
                )
            if actor_name in {"faq_agent", "stock_agent", "image_intake_agent"}:
                specialist_result = ctx.run_specialist(actor_name, phase="swarm")
            ctx.emit("node", "completed", "completed", actor_name=actor_name, node_id=node_id, payload={"stage": "handoff_loop", "position": index})

        # Review gate
        review_required = should_request_review(text)
        if review_required:
            ctx.emit(
                "review",
                "required",
                "human_review_required",
                actor_name="swarm_coordinator",
                node_id="swarm.review",
                payload=request_human_review("Swarm escalation policy triggered review."),
            )

        # Compose and emit final response
        final_text = ctx.compose_response(
            architecture="decentralized_swarm",
            route=route,
            specialist_result=specialist_result or {},
            review_required=review_required,
        )
        ctx.emit_partial(final_text)
        ctx.emit(
            "response",
            "final",
            "completed",
            actor_name="swarm_synthesizer",
            node_id="swarm.final",
            payload={"contentText": final_text, "reviewRequired": review_required},
        )
        ctx.emit("run", "completed", "completed", payload={"phase": "completed", "reviewRequired": review_required})
        return ctx.build_result(final_text, review_required)
