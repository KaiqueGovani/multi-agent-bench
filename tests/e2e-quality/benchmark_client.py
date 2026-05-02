"""Benchmark client that wraps E2EClient to collect RunMetrics per scenario."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from _loader import REPO_ROOT, resolve_case_attachments
from api_client import E2EClient


@dataclass(frozen=True)
class RunMetrics:
    """Metrics collected from a single benchmark execution.

    See docs/roadmap/02-architecture-benchmark.md section 4.2.
    """

    # Identification
    run_id: str
    architecture_mode: str
    scenario_id: str
    iteration: int

    # Routing
    route: str | None = None
    final_actor: str | None = None

    # Performance
    latency_ms: float = 0.0

    # Tokens
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    # Complexity
    tool_call_count: int = 0
    tool_error_count: int = 0
    loop_count: int = 0
    handoff_count: int = 0

    # Quality
    review_required: bool = False
    content_text: str = ""  # preview, truncated to 120 chars

    # Runtime info (from run record's experiment metadata)
    model_provider: str | None = None
    model_name: str | None = None

    # Status
    success: bool = True
    error: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


class BenchmarkClient:
    """Thin wrapper over E2EClient that runs one scenario case and returns RunMetrics.

    This client does NOT manage the runtime. The caller is responsible for ensuring
    API_BASE_URL is reachable and (for live mode) that ENABLE_LIVE_LLM is set on the
    runtime process. This client only consumes the chat-api wire contract.
    """

    def __init__(self, e2e_client: E2EClient) -> None:
        self._client = e2e_client

    _TERMINAL_STATUSES = frozenset({"completed", "failed", "human_review_required", "cancelled"})

    def _poll_run_until_terminal(self, run_id: str, *, timeout: float) -> dict:
        """Poll GET /runs/{run_id} until the run reaches a terminal status."""
        deadline = time.monotonic() + timeout
        while True:
            run = self._client.get_run(run_id)
            if run.get("status") in self._TERMINAL_STATUSES:
                return run
            if time.monotonic() >= deadline:
                return run
            time.sleep(0.3)

    def run_and_collect(
        self,
        *,
        case: dict,
        architecture: str,
        iteration: int,
        timeout: float,
    ) -> RunMetrics:
        """Execute one case on the given architecture and return metrics.

        Flow: create_conversation(metadata={architectureMode: arch}) -> send_message
        -> wait_for_event 'response.final' (carries route/finalActor/reviewRequired/contentText)
        -> poll GET /runs/{run_id} until terminal status.

        We skip waiting for processing.completed because human_review_required
        runs emit review.required instead (in the external runtime path), which
        would cause a timeout. Polling the run record is authoritative for both
        terminal states and carries the summary metrics.

        Latency is measured as wall-clock time from send_message to response.final,
        giving consistent user-perceived latency regardless of terminal state.
        """
        scenario_id = str(case["id"])
        text = str(case["input"]["text"])
        metadata = {"architectureMode": architecture}

        try:
            # Resolve attachments (same logic as test_e2e.py)
            attachments = resolve_case_attachments(case)

            expected_status = case.get("expected", {}).get("http_status", 202)

            conversation_id = self._client.create_conversation(metadata=metadata)

            t0 = time.monotonic()
            msg_resp = self._client.send_message(
                conversation_id, text, metadata=metadata,
                attachments=attachments, expected_status=expected_status,
            )

            # Error-path early return (e.g. anexo_invalido expects 400)
            if expected_status >= 400:
                latency_ms = (time.monotonic() - t0) * 1000.0
                return RunMetrics(
                    run_id="",
                    architecture_mode=architecture,
                    scenario_id=scenario_id,
                    iteration=iteration,
                    latency_ms=latency_ms,
                    content_text=(msg_resp.get("error") or "")[:120],
                    success=True,
                )

            final_event = self._client.wait_for_event(
                conversation_id, "response.final", timeout=timeout,
            )

            latency_ms = (time.monotonic() - t0) * 1000.0

            # Extract from response.final (flat payload)
            fp = final_event.get("payload", {})

            # Resolve runId: prefer send_message response, then response.final payload
            run_id = msg_resp.get("runId") or fp.get("runId") or ""

            # Fetch authoritative run record from the API.
            # Poll until the run reaches a terminal status (completed,
            # human_review_required, failed, or cancelled).
            summary: dict = {}
            experiment: dict = {}
            if run_id:
                run_record = self._poll_run_until_terminal(run_id, timeout=timeout)
                summary = run_record.get("summary") or {}
                experiment = run_record.get("experiment") or {}

            input_tokens = summary.get("inputTokens") or 0
            output_tokens = summary.get("outputTokens") or 0
            total_tokens = summary.get("totalTokens") or (input_tokens + output_tokens)

            return RunMetrics(
                run_id=run_id,
                architecture_mode=architecture,
                scenario_id=scenario_id,
                iteration=iteration,
                route=fp.get("route"),
                final_actor=fp.get("finalActor"),
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                tool_call_count=summary.get("toolCallCount") or 0,
                tool_error_count=summary.get("toolErrorCount") or 0,
                loop_count=summary.get("loopCount") or 0,
                handoff_count=summary.get("handoffCount") or 0,
                review_required=bool(fp.get("reviewRequired", False)),
                content_text=(fp.get("contentText") or "")[:120],
                model_provider=experiment.get("modelProvider"),
                model_name=experiment.get("modelName"),
                success=True,
            )

        except Exception as exc:
            return RunMetrics(
                run_id="",
                architecture_mode=architecture,
                scenario_id=scenario_id,
                iteration=iteration,
                success=False,
                error=str(exc)[:500],
            )
