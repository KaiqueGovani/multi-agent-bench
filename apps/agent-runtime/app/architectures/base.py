"""Base types and shared execution context for architecture implementations.

ExecutionContext encapsulates all mutable state and helper methods that
architecture executors need during a run.  ArchitectureExecutor is the
Protocol every concrete architecture must satisfy.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Protocol
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


logger = logging.getLogger(__name__)


def _coerce_tool_result(result: Any) -> dict:
    """Best-effort conversion of a tool result to a JSON-serializable dict."""
    if isinstance(result, dict):
        return result
    for attr in ("content", "result", "output"):
        value = getattr(result, attr, None)
        if isinstance(value, dict):
            return value
    return {"value": str(result)[:1000]}


# ---------------------------------------------------------------------------
# _StreamBuffer — coalesces LLM streaming chunks into response.partial events
# ---------------------------------------------------------------------------

class _StreamBuffer:
    """Buffers LLM text chunks and flushes as coalesced ``response.partial`` events.

    Thread-safe: uses a ``threading.Lock`` because Strands ``callback_handler``
    may be invoked from the model's worker thread, not the main asyncio thread.
    The lock serialises access to ``_buf`` and ``_accumulated`` so concurrent
    appends and flushes never see torn state.
    """

    FLUSH_CHARS = 200
    FLUSH_MS = 250

    def __init__(self, ctx: "ExecutionContext", actor_name: str) -> None:
        self._ctx = ctx
        self._actor = actor_name
        self._buf: list[str] = []
        self._accumulated = ""  # full text so far (cumulative)
        self._lock = threading.Lock()
        self._last_flush_ms: float = 0.0

    def append(self, chunk: str) -> None:
        """Add a chunk; flush if char or time threshold exceeded."""
        with self._lock:
            self._buf.append(chunk)
            self._accumulated += chunk
            unflushed = "".join(self._buf)
            now_ms = time.monotonic() * 1000
            if len(unflushed) >= self.FLUSH_CHARS or (now_ms - self._last_flush_ms) >= self.FLUSH_MS:
                self._flush_locked(now_ms)

    def flush_final(self) -> None:
        """Flush any remaining buffered content.  Called in a ``finally`` block."""
        with self._lock:
            if self._buf:
                self._flush_locked(time.monotonic() * 1000)

    def _flush_locked(self, now_ms: float) -> None:
        """Emit a ``response.partial`` with the cumulative text.  Must hold ``_lock``."""
        try:
            self._ctx.emit_partial(self._accumulated)
        except Exception as exc:
            logger.warning("stream buffer flush failed: %s", exc)
        self._buf = []
        self._last_flush_ms = now_ms


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
    handoff_count: int
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
        self.handoff_count: int = 0
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

    def emit_reasoning(
        self,
        actor_name: str,
        node_id: str,
        thought: str,
        decision: str,
        candidates: list[str] | None = None,
    ) -> None:
        """Emit an actor.reasoning event."""
        payload: dict = {"thought": thought, "decision": decision}
        if candidates is not None:
            payload["candidates"] = candidates
        self.emit(
            "actor",
            "reasoning",
            "completed",
            actor_name=actor_name,
            node_id=node_id,
            payload=payload,
        )

    def emit_message(self, actor_name: str, node_id: str, text: str) -> None:
        """Emit an actor.message event."""
        self.emit(
            "actor",
            "message",
            "completed",
            actor_name=actor_name,
            node_id=node_id,
            payload={"text": text},
        )

    def emit_final(
        self,
        final_text: str,
        *,
        route: str,
        final_actor: str,
        architecture_mode: str,
        review_required: bool,
    ) -> None:
        """Emit response.partial + response.final with enriched payload."""
        self.emit_partial(final_text)
        self.emit(
            "response",
            "final",
            "completed",
            actor_name=final_actor,
            node_id=f"{final_actor}.respond",
            payload={
                "contentText": final_text,
                "route": route,
                "finalActor": final_actor,
                "architectureMode": architecture_mode,
                "reviewRequired": review_required,
            },
        )
        self.emit(
            "node", "completed", "completed",
            actor_name="response_streamer",
            node_id="response_streamer.completed",
        )

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
        live_text = self.invoke_live_agent(
            system_prompt=(
                "Você é um agente de atendimento de farmácia. Responda em português do Brasil, "
                "em prosa corrida, sem fornecer dosagens específicas. Quando apropriado, sugira "
                "consultar um farmacêutico."
            ),
            prompt=(
                f"Informação coletada pelo especialista: {specialist_result}. "
                "Componha a resposta final ao usuário."
            ),
        )
        if live_text:
            return live_text
        return (
            f"[modo mock] Resposta fixa da arquitetura {architecture}. "
            "Ative ENABLE_LIVE_LLM=true com AWS_BEARER_TOKEN_BEDROCK configurado "
            "para respostas reais via LLM."
        )

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
            handoff_count=self.handoff_count,
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
            agent = Agent(model=model, system_prompt=system_prompt)
            result = agent(prompt)
            return str(result).strip()
        except Exception:
            self.tool_error_count += 1
            return None

    def _build_tool_hook_provider(
        self,
        actor_name: str,
        tool_calls_sink: list[dict] | None = None,
    ) -> Any:
        """Build a _ToolHookProvider that emits tool.started / tool.completed events.

        If *tool_calls_sink* is provided, each tool invocation is also appended to it
        (matching the behaviour previously inlined in ``invoke_live_supervisor``).
        """
        try:
            from strands.hooks import BeforeToolCallEvent, AfterToolCallEvent
        except ImportError:  # pragma: no cover
            return None

        ctx = self  # capture for closures

        def on_before_tool(event):
            name = event.tool_use.get("name")
            args = event.tool_use.get("input", {})
            ctx.tool_call_count += 1
            ctx.emit(
                "tool", "started", "running",
                actor_name=actor_name, tool_name=name,
                node_id=f"{actor_name}.tool.{name}",
                payload={"input": args},
            )
            if tool_calls_sink is not None:
                tool_calls_sink.append({"name": name, "input": args, "result": None})

        def on_after_tool(event):
            name = event.tool_use.get("name")
            result_payload = _coerce_tool_result(event.result)
            ctx.emit(
                "tool", "completed", "completed",
                actor_name=actor_name, tool_name=name,
                node_id=f"{actor_name}.tool.{name}",
                payload={"result": result_payload},
            )
            if tool_calls_sink is not None:
                for tc in reversed(tool_calls_sink):
                    if tc["name"] == name and tc["result"] is None:
                        tc["result"] = result_payload
                        break

        class _ToolHookProvider:
            """HookProvider that registers tool-boundary callbacks with explicit event types.

            We use an explicit HookProvider (rather than `hooks=[fn, fn]`) because our module
            uses `from __future__ import annotations`, which turns type hints into strings and
            breaks Strands' automatic event type inference from function signatures.
            """

            def register_hooks(self, registry, **_kwargs):
                registry.add_callback(BeforeToolCallEvent, on_before_tool)
                registry.add_callback(AfterToolCallEvent, on_after_tool)

        return _ToolHookProvider()

    def invoke_live_supervisor(
        self,
        *,
        system_prompt: str,
        user_message: str,
        tools: list,
        supervisor_actor: str = "supervisor_agent",
    ) -> tuple[str, list[dict]] | None:
        """Run a Strands Agent with full instrumentation.

        Returns (final_text, tool_calls) or None if live LLM is disabled or fails.
        """
        if not self.settings.enable_live_llm:
            return None
        if Agent is None or BedrockModel is None:
            return None

        tool_calls: list[dict] = []
        hook_provider = self._build_tool_hook_provider(supervisor_actor, tool_calls_sink=tool_calls)
        if hook_provider is None:  # pragma: no cover
            return None

        buffer = _StreamBuffer(self, supervisor_actor)

        def callback_handler(**kwargs: Any) -> None:
            if "data" in kwargs and kwargs["data"]:
                text_chunk = str(kwargs["data"])
                if text_chunk.strip():
                    buffer.append(text_chunk)

        try:
            model = BedrockModel(
                model_id=self.settings.bedrock_model_id,
                region_name=self.settings.aws_region,
            )
            agent = Agent(
                model=model,
                system_prompt=system_prompt,
                tools=tools,
                hooks=[hook_provider],
                callback_handler=callback_handler,
            )
            result = agent(user_message)
            return str(result).strip(), tool_calls
        except Exception as exc:  # pragma: no cover - network path
            self.tool_error_count += 1
            self.emit(
                "run", "error", "failed",
                payload={"phase": "live_supervisor", "error": str(exc)[:500]},
            )
            return None
        finally:
            try:
                buffer.flush_final()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("final stream flush failed in invoke_live_supervisor: %s", exc)

    def create_agent(
        self,
        *,
        system_prompt: str,
        tools: list | None = None,
        actor_name: str,
    ) -> Any | None:
        """Create a Strands Agent with BedrockModel and tool-boundary hook instrumentation.

        Returns None if live LLM is disabled or Strands is unavailable. The returned Agent,
        when invoked, emits `tool.started` / `tool.completed` events (via the same BeforeToolCallEvent
        / AfterToolCallEvent hook logic already used by `invoke_live_supervisor`), increments
        `self.tool_call_count`, and streams text chunks via `emit_message(actor_name, ...)`.
        """
        if not self.settings.enable_live_llm:
            return None
        if Agent is None or BedrockModel is None:
            return None

        hook_provider = self._build_tool_hook_provider(actor_name)
        if hook_provider is None:  # pragma: no cover
            return None

        buffer = _StreamBuffer(self, actor_name)

        def callback_handler(**kwargs: Any) -> None:
            if "data" in kwargs and kwargs["data"]:
                text_chunk = str(kwargs["data"])
                if text_chunk.strip():
                    buffer.append(text_chunk)

        try:
            model = BedrockModel(
                model_id=self.settings.bedrock_model_id,
                region_name=self.settings.aws_region,
            )
            agent = Agent(
                model=model,
                system_prompt=system_prompt,
                tools=tools or [],
                hooks=[hook_provider],
                callback_handler=callback_handler,
            )
            # NOTE: flush_final is NOT called here because the Agent is returned
            # to the caller — the caller is responsible for invoking the agent and
            # flushing the buffer afterwards.  We attach the buffer to the agent so
            # callers can call buffer.flush_final() in their own finally block.
            agent._stream_buffer = buffer  # type: ignore[attr-defined]
            return agent
        except Exception:  # pragma: no cover - network path
            self.tool_error_count += 1
            try:
                buffer.flush_final()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("final stream flush failed in create_agent: %s", exc)
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
