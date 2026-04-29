from __future__ import annotations

import json
from datetime import UTC, datetime
from urllib.request import Request, urlopen

from app.core.config import get_settings
from app.schemas.runtime import (
    CompleteRunRequest,
    IngestRunExecutionEventRequest,
    RuntimeCallbackConfig,
    RunSummary,
)


class ChatApiCallbacks:
    def __init__(self, callback: RuntimeCallbackConfig) -> None:
        self._callback = callback
        self._settings = get_settings()

    def emit_run_event(self, event: IngestRunExecutionEventRequest) -> None:
        self._post(
            "/integrations/ai/run-events",
            event.model_dump(by_alias=True, mode="json", exclude_none=True),
        )

    def complete_run(
        self,
        *,
        run_id: str,
        status: str,
        trace_id: str | None,
        total_duration_ms: int,
        human_review_required: bool,
        final_outcome: str,
        summary: RunSummary,
    ) -> None:
        request = CompleteRunRequest(
            status=status,
            trace_id=trace_id,
            finished_at=datetime.now(UTC),
            total_duration_ms=total_duration_ms,
            human_review_required=human_review_required,
            final_outcome=final_outcome,
            summary=summary,
        )
        self._patch(
            f"/runs/{run_id}",
            request.model_dump(by_alias=True, mode="json", exclude_none=True),
        )

    def _post(self, path: str, payload: dict) -> None:
        request = Request(
            self._callback.base_url.rstrip("/") + path,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers=self._headers(),
        )
        with urlopen(request, timeout=self._settings.chat_api_callback_timeout_seconds):
            return

    def _patch(self, path: str, payload: dict) -> None:
        request = Request(
            self._callback.base_url.rstrip("/") + path,
            data=json.dumps(payload).encode("utf-8"),
            method="PATCH",
            headers=self._headers(),
        )
        with urlopen(request, timeout=self._settings.chat_api_callback_timeout_seconds):
            return

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        if self._callback.api_key:
            headers["X-API-Key"] = self._callback.api_key
        if self._callback.ai_service_secret:
            headers["X-AI-Service-Secret"] = self._callback.ai_service_secret
        return headers
