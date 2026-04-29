from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from uuid import uuid4

from app.core.config import Settings, get_settings
from app.schemas.runtime import (
    IngestRunExecutionEventRequest,
    RunSummary,
    RuntimeDispatchRequest,
)
from app.services.callbacks import ChatApiCallbacks
from app.tools.domain_tools import (
    attachment_intake,
    faq_lookup,
    infer_route,
    request_human_review,
    should_request_review,
    stock_lookup,
)

try:  # pragma: no cover - optional dependency integration
    from strands import Agent
    from strands.models.bedrock import BedrockModel
except Exception:  # pragma: no cover
    Agent = None
    BedrockModel = None


@dataclass
class ExecutionResult:
    final_text: str
    final_outcome: str
    human_review_required: bool
    tool_call_count: int
    tool_error_count: int
    loop_count: int
    trace_id: str
    time_to_first_public_event_ms: int | None = None
    time_to_first_partial_response_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class RuntimeExecutor:
    def __init__(self, request: RuntimeDispatchRequest) -> None:
        self.request = request
        self.settings = get_settings()
        self.callbacks = ChatApiCallbacks(request.callback)
        self.started_at = time.perf_counter()
        self.first_public_event_ms: int | None = None
        self.first_partial_response_ms: int | None = None
        self.tool_call_count = 0
        self.tool_error_count = 0
        self.loop_count = 0
        self.trace_id = self._trace_id()

    def execute(self) -> ExecutionResult:
        architecture = self.request.architecture_mode
        self.emit("run", "started", "running", payload={"phase": "dispatch", "architectureMode": architecture})
        if architecture == "structured_workflow":
            return self._execute_workflow()
        if architecture == "decentralized_swarm":
            return self._execute_swarm()
        return self._execute_centralized()

    def _execute_centralized(self) -> ExecutionResult:
        text = self.request.latest_message.content_text or ""
        route = infer_route(text, self._attachment_dicts())
        specialist_actor = self._specialist_actor(route)
        self.emit(
            "node",
            "started",
            "running",
            actor_name="supervisor_agent",
            node_id="supervisor.classify",
            payload={"phase": "routing", "text": text, "route": route},
        )
        self.emit(
            "node",
            "completed",
            "completed",
            actor_name="supervisor_agent",
            node_id="supervisor.classify",
            payload={"route": route},
        )
        self.emit(
            "handoff",
            "requested",
            "running",
            actor_name="supervisor_agent",
            node_id="handoff.specialist",
            payload={"route": route, "targetActor": specialist_actor},
        )
        specialist_result = self._run_specialist(specialist_actor, phase="specialist")
        review_required = should_request_review(text)
        if review_required:
            review_result = request_human_review("Content requires human review by policy.")
            self.emit(
                "review",
                "required",
                "human_review_required",
                actor_name="supervisor_agent",
                node_id="supervisor.review_gate",
                payload=review_result,
            )
        final_text = self._compose_response(
            architecture="centralized_orchestration",
            route=route,
            specialist_result=specialist_result,
            review_required=review_required,
        )
        self.emit_partial(final_text)
        self.emit(
            "response",
            "final",
            "completed",
            actor_name="supervisor_agent",
            node_id="supervisor.respond",
            payload={"contentText": final_text, "reviewRequired": review_required},
        )
        self.emit(
            "run",
            "completed",
            "completed",
            payload={"phase": "completed", "reviewRequired": review_required},
        )
        return self._result(final_text, review_required)

    def _execute_workflow(self) -> ExecutionResult:
        text = self.request.latest_message.content_text or ""
        route = infer_route(text, self._attachment_dicts())
        specialist_actor = self._specialist_actor(route)
        stages = [
            ("workflow.classify", "router_agent", {"stage": "classify", "route": route}),
            ("workflow.evidence", "workflow_evidence_agent", {"stage": "gather_evidence"}),
        ]
        if self._attachment_dicts():
            stages.append(
                ("workflow.multimodal", "workflow_multimodal_agent", {"stage": "multimodal_analysis"})
            )
        stages.extend(
            [
                ("workflow.review", "workflow_review_agent", {"stage": "review_gate"}),
                ("workflow.synthesize", "workflow_synthesis_agent", {"stage": "synthesize"}),
            ]
        )
        specialist_result = None
        for node_id, actor_name, payload in stages:
            self.emit("node", "started", "running", actor_name=actor_name, node_id=node_id, payload=payload)
            if node_id == "workflow.evidence":
                specialist_result = self._run_specialist(specialist_actor, phase="workflow")
            self.emit("node", "completed", "completed", actor_name=actor_name, node_id=node_id, payload=payload)
        review_required = should_request_review(text)
        if review_required:
            self.emit(
                "review",
                "required",
                "human_review_required",
                actor_name="workflow_review_agent",
                node_id="workflow.review",
                payload=request_human_review("Workflow review gate escalated the run."),
            )
        final_text = self._compose_response(
            architecture="structured_workflow",
            route=route,
            specialist_result=specialist_result or {},
            review_required=review_required,
        )
        self.emit_partial(final_text)
        self.emit(
            "response",
            "final",
            "completed",
            actor_name="workflow_synthesis_agent",
            node_id="workflow.synthesize",
            payload={"contentText": final_text, "reviewRequired": review_required},
        )
        self.emit("run", "completed", "completed", payload={"phase": "completed", "reviewRequired": review_required})
        return self._result(final_text, review_required)

    def _execute_swarm(self) -> ExecutionResult:
        text = self.request.latest_message.content_text or ""
        route = infer_route(text, self._attachment_dicts())
        specialist_actor = self._specialist_actor(route)
        chain = ["swarm_coordinator", specialist_actor]
        if specialist_actor != "faq_agent":
            chain.append("faq_agent")
        chain.append("swarm_synthesizer")
        specialist_result = None
        for index, actor_name in enumerate(chain):
            node_id = f"swarm.{index}.{actor_name}"
            self.emit("node", "started", "running", actor_name=actor_name, node_id=node_id, payload={"stage": "handoff_loop", "position": index})
            if index > 0:
                self.loop_count += 1
                self.emit(
                    "handoff",
                    "requested",
                    "running",
                    actor_name=chain[index - 1],
                    node_id=f"swarm.handoff.{index}",
                    payload={"from": chain[index - 1], "to": actor_name, "hop": index},
                )
            if actor_name in {"faq_agent", "stock_agent", "image_intake_agent"}:
                specialist_result = self._run_specialist(actor_name, phase="swarm")
            self.emit("node", "completed", "completed", actor_name=actor_name, node_id=node_id, payload={"stage": "handoff_loop", "position": index})
        review_required = should_request_review(text)
        if review_required:
            self.emit(
                "review",
                "required",
                "human_review_required",
                actor_name="swarm_coordinator",
                node_id="swarm.review",
                payload=request_human_review("Swarm escalation policy triggered review."),
            )
        final_text = self._compose_response(
            architecture="decentralized_swarm",
            route=route,
            specialist_result=specialist_result or {},
            review_required=review_required,
        )
        self.emit_partial(final_text)
        self.emit(
            "response",
            "final",
            "completed",
            actor_name="swarm_synthesizer",
            node_id="swarm.final",
            payload={"contentText": final_text, "reviewRequired": review_required},
        )
        self.emit("run", "completed", "completed", payload={"phase": "completed", "reviewRequired": review_required})
        return self._result(final_text, review_required)

    def _run_specialist(self, actor_name: str, *, phase: str) -> dict:
        self.emit("node", "started", "running", actor_name=actor_name, node_id=f"{phase}.{actor_name}", payload={"phase": phase})
        try:
            if actor_name == "stock_agent":
                self.tool_call_count += 1
                self.emit("tool", "started", "running", actor_name=actor_name, tool_name="stock_lookup", node_id=f"{phase}.{actor_name}.tool", payload={"phase": phase})
                result = stock_lookup(self.request.latest_message.content_text or "")
                self.emit("tool", "completed", "completed", actor_name=actor_name, tool_name="stock_lookup", node_id=f"{phase}.{actor_name}.tool", payload=result)
            elif actor_name == "image_intake_agent":
                self.tool_call_count += 1
                self.emit("tool", "started", "running", actor_name=actor_name, tool_name="attachment_intake", node_id=f"{phase}.{actor_name}.tool", payload={"phase": phase})
                result = attachment_intake(self._attachment_dicts())
                self.emit("tool", "completed", "completed", actor_name=actor_name, tool_name="attachment_intake", node_id=f"{phase}.{actor_name}.tool", payload=result)
            else:
                self.tool_call_count += 1
                self.emit("tool", "started", "running", actor_name=actor_name, tool_name="faq_lookup", node_id=f"{phase}.{actor_name}.tool", payload={"phase": phase})
                result = faq_lookup(self.request.latest_message.content_text or "")
                self.emit("tool", "completed", "completed", actor_name=actor_name, tool_name="faq_lookup", node_id=f"{phase}.{actor_name}.tool", payload=result)
        except Exception as exc:  # pragma: no cover - defensive
            self.tool_error_count += 1
            self.emit("tool", "failed", "failed", actor_name=actor_name, tool_name="domain_tool", node_id=f"{phase}.{actor_name}.tool", payload={"reason": str(exc)})
            result = {"error": str(exc)}
        self.emit("node", "completed", "completed", actor_name=actor_name, node_id=f"{phase}.{actor_name}", payload=result)
        return result

    def _compose_response(
        self,
        *,
        architecture: str,
        route: str,
        specialist_result: dict,
        review_required: bool,
    ) -> str:
        header = {
            "centralized_orchestration": "Supervisor central concluiu a coordenação.",
            "structured_workflow": "Workflow estruturado concluiu as etapas planejadas.",
            "decentralized_swarm": "Swarm concluiu a colaboração entre agentes.",
        }[architecture]
        prompt = (
            f"Arquitetura: {architecture}\n"
            f"Rota: {route}\n"
            f"Review required: {review_required}\n"
            f"Evidencia estruturada: {specialist_result}\n"
            "Gere uma resposta curta em portugues do Brasil para a POC, sem alegar decisao clinica real."
        )
        live_text = self._invoke_live_agent(
            system_prompt=(
                "Voce compoe respostas de um runtime experimental multiagente para farmacia. "
                "Nao invente integracoes reais, nao forneca aconselhamento clinico e cite quando houver revisao humana."
            ),
            prompt=prompt,
        )
        if live_text:
            return live_text
        if review_required:
            return f"{header} O caso foi sinalizado para revisao humana. Evidencia principal: {specialist_result}."
        return f"{header} Rota aplicada: {route}. Evidencia principal: {specialist_result}. Resposta gerada com politicas controladas da POC."

    def emit_partial(self, final_text: str) -> None:
        preview = final_text[:160]
        self.emit(
            "response",
            "partial",
            "running",
            actor_name="response_streamer",
            node_id="response.partial",
            payload={"contentText": preview},
        )
        if self.first_partial_response_ms is None:
            self.first_partial_response_ms = self.elapsed_ms()

    def emit(
        self,
        family: str,
        name: str,
        status: str,
        *,
        actor_name: str | None = None,
        node_id: str | None = None,
        tool_name: str | None = None,
        payload: dict | None = None,
    ) -> None:
        event = IngestRunExecutionEventRequest(
            run_id=self.request.run_id,
            conversation_id=self.request.conversation_id,
            message_id=self.request.message_id,
            correlation_id=self.request.correlation_id,
            event_family=family,
            event_name=name,
            status=status,
            actor_name=actor_name,
            node_id=node_id,
            tool_name=tool_name,
            source="ai_service",
            external_event_id=f"{self.request.run_id}:{family}:{name}:{uuid4()}",
            duration_ms=self.elapsed_ms(),
            payload=payload or {},
        )
        self.callbacks.emit_run_event(event)
        if self.first_public_event_ms is None:
            self.first_public_event_ms = self.elapsed_ms()

    def _result(self, final_text: str, review_required: bool) -> ExecutionResult:
        input_tokens = max(1, len((self.request.latest_message.content_text or "").split()) * 5)
        output_tokens = max(1, len(final_text.split()) * 5)
        return ExecutionResult(
            final_text=final_text,
            final_outcome="human_review_required" if review_required else "answered",
            human_review_required=review_required,
            tool_call_count=self.tool_call_count,
            tool_error_count=self.tool_error_count,
            loop_count=self.loop_count,
            trace_id=self.trace_id,
            time_to_first_public_event_ms=self.first_public_event_ms,
            time_to_first_partial_response_ms=self.first_partial_response_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )

    def _attachment_dicts(self) -> list[dict]:
        return [
            attachment.model_dump(by_alias=True, mode="json", exclude_none=True)
            for attachment in self.request.latest_message.attachments
        ]

    @staticmethod
    def _specialist_actor(route: str) -> str:
        mapping = {
            "faq": "faq_agent",
            "stock_lookup": "stock_agent",
            "image_intake": "image_intake_agent",
        }
        return mapping.get(route, "faq_agent")

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self.started_at) * 1000)

    def _trace_id(self) -> str:
        base = f"{self.request.run_id}:{self.request.message_id}:{self.request.traceparent or ''}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]

    def _invoke_live_agent(self, *, system_prompt: str, prompt: str) -> str | None:
        if not self.settings.enable_live_llm:
            return None
        if Agent is None or BedrockModel is None:
            return None
        try:
            model = BedrockModel(
                model_id=self.settings.bedrock_model_id,
                region_name=self.settings.aws_region,
            )
            agent = Agent(
                model=model,
                system_prompt=system_prompt,
            )
            result = agent(prompt)
            text = getattr(result, "message", None) or getattr(result, "output", None) or str(result)
            if hasattr(result, "metrics"):
                metrics = getattr(result, "metrics")
                input_tokens = getattr(metrics, "input_tokens", None)
                output_tokens = getattr(metrics, "output_tokens", None)
                if isinstance(input_tokens, int):
                    self.tool_call_count += 0
                if isinstance(output_tokens, int):
                    self.tool_call_count += 0
            return str(text).strip()
        except Exception:
            self.tool_error_count += 1
            return None


class RuntimeExecutionService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def execute_run(self, request: RuntimeDispatchRequest) -> ExecutionResult:
        executor = RuntimeExecutor(request)
        result = executor.execute()
        executor.callbacks.complete_run(
            run_id=str(request.run_id),
            status="human_review_required" if result.human_review_required else "completed",
            trace_id=result.trace_id,
            total_duration_ms=executor.elapsed_ms(),
            human_review_required=result.human_review_required,
            final_outcome=result.final_outcome,
            summary=RunSummary(
                time_to_first_public_event_ms=result.time_to_first_public_event_ms,
                time_to_first_partial_response_ms=result.time_to_first_partial_response_ms,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                total_tokens=result.total_tokens,
                tool_call_count=result.tool_call_count,
                tool_error_count=result.tool_error_count,
                loop_count=result.loop_count,
                stop_reason="completed",
                final_outcome=result.final_outcome,
            ),
        )
        return result
