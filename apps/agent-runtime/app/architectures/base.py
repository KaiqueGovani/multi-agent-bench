"""Base types and shared execution context for architecture implementations.

ExecutionContext encapsulates all mutable state and helper methods that
architecture executors need during a run.  ArchitectureExecutor is the
Protocol every concrete architecture must satisfy.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from app.core.config import Settings, get_settings
from app.schemas.runtime import (
    IngestRunExecutionEventRequest,
    RuntimeDispatchRequest,
)
from app.services.callbacks import ChatApiCallbacks
from app.tools.domain_tools import (
    attachment_intake,
    faq_lookup,
    stock_lookup,
)

# Optional dependency — Strands SDK for live LLM calls
try:  # pragma: no cover - optional dependency integration
    from strands import Agent
    from strands.models.bedrock import BedrockModel
except Exception:  # pragma: no cover
    Agent = None
    BedrockModel = None


# ---------------------------------------------------------------------------
# ExecutionResult — returned by every architecture executor
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# ExecutionContext — shared state + helpers available to every architecture
# ---------------------------------------------------------------------------

class ExecutionContext:
    """Holds request data, mutable counters, and helper methods shared across
    all architecture implementations."""

    def __init__(
        self,
        request: RuntimeDispatchRequest,
        callbacks: ChatApiCallbacks,
        settings: Settings,
        started_at: float,
        trace_id: str,
    ) -> None:
        self.request = request
        self.callbacks = callbacks
        self.settings = settings
        self.started_at = started_at
        self.trace_id = trace_id

        # Mutable counters — updated by helpers and architecture executors
        self.tool_call_count: int = 0
        self.tool_error_count: int = 0
        self.loop_count: int = 0
        self.first_public_event_ms: int | None = None
        self.first_partial_response_ms: int | None = None

    # -- Event emission -------------------------------------------------------

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

    # -- Specialist execution -------------------------------------------------

    def run_specialist(self, actor_name: str, *, phase: str) -> dict:
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
                result = attachment_intake(self.attachment_dicts())
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

    # -- Response composition -------------------------------------------------

    def compose_response(
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
        live_text = self.invoke_live_agent(
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

    # -- Result builder -------------------------------------------------------

    def build_result(self, final_text: str, review_required: bool) -> ExecutionResult:
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

    # -- Utility helpers ------------------------------------------------------

    def attachment_dicts(self) -> list[dict]:
        return [
            attachment.model_dump(by_alias=True, mode="json", exclude_none=True)
            for attachment in self.request.latest_message.attachments
        ]

    @staticmethod
    def specialist_actor(route: str) -> str:
        mapping = {
            "faq": "faq_agent",
            "stock_lookup": "stock_agent",
            "image_intake": "image_intake_agent",
        }
        return mapping.get(route, "faq_agent")

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self.started_at) * 1000)

    def invoke_live_agent(self, *, system_prompt: str, prompt: str) -> str | None:
        """Call Strands Agent with Bedrock when ENABLE_LIVE_LLM is on."""
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
            return str(text).strip()
        except Exception:
            self.tool_error_count += 1
            return None

    # -- Static factory helpers used by RuntimeExecutor -----------------------

    @staticmethod
    def make_trace_id(request: RuntimeDispatchRequest) -> str:
        base = f"{request.run_id}:{request.message_id}:{request.traceparent or ''}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------
# ArchitectureExecutor — Protocol that every architecture must implement
# ---------------------------------------------------------------------------

class ArchitectureExecutor(Protocol):
    """Contract for pluggable architecture implementations."""

    def execute(self, ctx: ExecutionContext) -> ExecutionResult: ...
