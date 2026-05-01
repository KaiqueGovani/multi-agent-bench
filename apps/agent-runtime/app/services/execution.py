from __future__ import annotations

import logging
import time

from app.architectures import get_executor
from app.architectures.base import ExecutionContext, ExecutionResult
from app.core.config import Settings, get_settings
from app.schemas.runtime import (
    RunSummary,
    RuntimeDispatchRequest,
)
from app.services.callbacks import ChatApiCallbacks

# Import architecture modules to trigger @register() side-effects
import app.architectures.centralized  # noqa: F401
import app.architectures.workflow  # noqa: F401
import app.architectures.swarm  # noqa: F401

logger = logging.getLogger(__name__)


class RuntimeExecutor:
    def __init__(self, request: RuntimeDispatchRequest) -> None:
        self.request = request
        self.settings = get_settings()
        self.callbacks = ChatApiCallbacks(request.callback)
        self.started_at = time.perf_counter()
        self.trace_id = ExecutionContext.make_trace_id(request)

    def execute(self) -> ExecutionResult:
        architecture = self.request.architecture_mode
        ctx = ExecutionContext(
            request=self.request,
            callbacks=self.callbacks,
            settings=self.settings,
            started_at=self.started_at,
            trace_id=self.trace_id,
        )
        ctx.emit("run", "started", "running", payload={"phase": "dispatch", "architectureMode": architecture})
        try:
            executor = get_executor(architecture)
        except KeyError:
            logger.error("Unknown architecture mode: %s", architecture)
            ctx.emit(
                "run",
                "failed",
                "failed",
                payload={"phase": "dispatch", "reason": f"Unknown architecture: {architecture}"},
            )
            return ExecutionResult(
                final_text=f"Erro: arquitetura desconhecida '{architecture}'.",
                final_outcome="failed",
                human_review_required=False,
                tool_call_count=0,
                tool_error_count=0,
                loop_count=0,
                trace_id=self.trace_id,
            )
        return executor.execute(ctx)

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self.started_at) * 1000)


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
