"""Structured workflow architecture.

A predefined pipeline of stages (classify → evidence → multimodal →
review → synthesize) processes the message sequentially.  Each stage is
handled by a dedicated agent with a fixed responsibility.
"""

from __future__ import annotations

from app.architectures import register
from app.architectures.base import ExecutionContext, ExecutionResult
from app.tools.domain_tools import infer_route, request_human_review, should_request_review


@register("structured_workflow")
class WorkflowExecutor:
    """Structured workflow: predefined pipeline stages with specialised agents."""

    def execute(self, ctx: ExecutionContext) -> ExecutionResult:
        text = ctx.request.latest_message.content_text or ""
        attachments = ctx.attachment_dicts()
        route = infer_route(text, attachments)
        specialist_actor = ctx.specialist_actor(route)

        # Build the stage pipeline dynamically
        stages: list[tuple[str, str, dict]] = [
            ("workflow.classify", "router_agent", {"stage": "classify", "route": route}),
            ("workflow.evidence", "workflow_evidence_agent", {"stage": "gather_evidence"}),
        ]
        if attachments:
            stages.append(
                ("workflow.multimodal", "workflow_multimodal_agent", {"stage": "multimodal_analysis"})
            )
        stages.extend(
            [
                ("workflow.review", "workflow_review_agent", {"stage": "review_gate"}),
                ("workflow.synthesize", "workflow_synthesis_agent", {"stage": "synthesize"}),
            ]
        )

        # Execute each stage in order
        specialist_result = None
        for node_id, actor_name, payload in stages:
            ctx.emit("node", "started", "running", actor_name=actor_name, node_id=node_id, payload=payload)
            if node_id == "workflow.evidence":
                specialist_result = ctx.run_specialist(specialist_actor, phase="workflow")
            ctx.emit("node", "completed", "completed", actor_name=actor_name, node_id=node_id, payload=payload)

        # Review gate
        review_required = should_request_review(text)
        if review_required:
            ctx.emit(
                "review",
                "required",
                "human_review_required",
                actor_name="workflow_review_agent",
                node_id="workflow.review",
                payload=request_human_review("Workflow review gate escalated the run."),
            )

        # Compose and emit final response
        final_text = ctx.compose_response(
            architecture="structured_workflow",
            route=route,
            specialist_result=specialist_result or {},
            review_required=review_required,
        )
        ctx.emit_partial(final_text)
        ctx.emit(
            "response",
            "final",
            "completed",
            actor_name="workflow_synthesis_agent",
            node_id="workflow.synthesize",
            payload={"contentText": final_text, "reviewRequired": review_required},
        )
        ctx.emit("run", "completed", "completed", payload={"phase": "completed", "reviewRequired": review_required})
        return ctx.build_result(final_text, review_required)
