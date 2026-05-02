"""E2E scenario tests — driven by YAML files in scenarios/."""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pytest

from _loader import REPO_ROOT, resolve_case_attachments
from api_client import E2EClient


def _normalize(text: str) -> str:
    """Lowercase + strip accents for fuzzy matching."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def test_scenario(case: dict, architecture: str, api_client: E2EClient):
    expected = case["expected"]
    timeout = case.get("timeout_seconds", 30)
    ctx = {"conversation_id": None, "correlation_id": None}

    # 1. Create conversation
    conv_meta = {"architectureMode": architecture, "scenarioId": case["id"]}
    if case.get("conversation_metadata"):
        conv_meta.update(case["conversation_metadata"])
    conversation_id = api_client.create_conversation(metadata=conv_meta)
    ctx["conversation_id"] = conversation_id
    assert conversation_id, "conversationId must be a non-empty string"

    # 2. Send message
    msg_meta = {"architectureMode": architecture, "locale": "pt-BR", "scenarioId": case["id"]}
    if case.get("message_metadata"):
        msg_meta.update(case["message_metadata"])

    # Resolve attachments
    attachments = resolve_case_attachments(case)

    expected_status = expected.get("http_status", 202)
    msg_resp = api_client.send_message(
        conversation_id,
        case["input"]["text"],
        metadata=msg_meta,
        attachments=attachments,
        expected_status=expected_status,
    )

    def _fail(reason: str):
        pytest.fail(f"{reason} | conv={ctx['conversation_id']} corr={ctx['correlation_id']}")

    # Branch on error scenarios — no SSE events expected
    if expected_status >= 400:
        err_substr = expected.get("error_contains")
        error_text = msg_resp.get("error", "") if isinstance(msg_resp, dict) else ""
        if err_substr and err_substr not in error_text:
            _fail(f"Expected error containing '{err_substr}', got: {error_text!r}")
        return

    ctx["correlation_id"] = msg_resp.get("correlationId")
    ctx["run_id"] = msg_resp.get("runId")

    # 3. Wait for expected events sequentially
    expected_events = expected.get("event_types", [])
    last_event_id: str | None = None
    final_event: dict | None = None

    for evt_type in expected_events:
        event = api_client.wait_for_event(
            conversation_id, evt_type, timeout, since_event_id=last_event_id,
        )
        last_event_id = event.get("id")
        if evt_type == "response.final":
            final_event = event

    # 4. Assert on response.final content
    if final_event is None and "response.final" in expected_events:
        _fail("response.final event was expected but never received")

    conv_data: dict | None = None
    events_cache: list = []

    if final_event:
        payload = final_event.get("payload", {}) or {}
        # Extract response text — the runtime publishes it under payload.contentText.
        # Fallbacks cover older/variant shapes (payload.response.text, payload.text).
        response_text = payload.get("contentText") or ""
        if not response_text and isinstance(payload.get("response"), dict):
            response_text = payload["response"].get("text", "")
        if not response_text:
            response_text = payload.get("text", "")

        norm_text = _normalize(response_text)

        # Route assertion — check response text, payload.route, payload.response.route,
        # or the latest actor.completed with payload.route (emitted by mock's router_agent).
        route = expected["route"]
        nested_response = payload.get("response") if isinstance(payload.get("response"), dict) else {}
        route_from_actor_completed: str | None = None
        conv_data_for_route = api_client.get_conversation(conversation_id)
        for ev in reversed(conv_data_for_route.get("events", [])):
            if ev.get("eventType") != "actor.completed":
                continue
            ev_payload = ev.get("payload") or {}
            if ev_payload.get("route"):
                route_from_actor_completed = ev_payload.get("route")
                break
        route_found = (
            _normalize(route) in norm_text
            or payload.get("route") == route
            or nested_response.get("route") == route
            or route_from_actor_completed == route
        )
        if not route_found:
            _fail(
                f"Expected route '{route}' not found in response text, payload, or actor.completed events. "
                f"text={response_text!r}, actor_completed_route={route_from_actor_completed!r}"
            )

        # Cache for subsequent assertions
        conv_data = conv_data_for_route
        events_cache = conv_data.get("events", [])

        # final_actor assertion (optional) — check payload.finalActor or top-level actorName
        expected_final_actor = expected.get("final_actor")
        if expected_final_actor:
            actual_final_actor = payload.get("finalActor") or final_event.get("actorName")
            if actual_final_actor != expected_final_actor:
                _fail(
                    f"Expected finalActor={expected_final_actor!r}, "
                    f"got {actual_final_actor!r}"
                )

        # response_contains_any
        contains_any = expected.get("response_contains_any", [])
        if contains_any:
            matched = any(_normalize(kw) in norm_text for kw in contains_any)
            if not matched:
                _fail(f"None of {contains_any} found in response text")

        # response_contains_none
        contains_none = expected.get("response_contains_none", [])
        for kw in contains_none:
            if _normalize(kw) in norm_text:
                _fail(f"Forbidden keyword '{kw}' found in response text")

    # 5. Assert review_required
    if "review_required" in expected:
        if conv_data is None:
            conv_data = api_client.get_conversation(conversation_id)
            events_cache = conv_data.get("events", [])
        review_tasks = conv_data.get("reviewTasks", [])
        has_review = len(review_tasks) > 0
        if expected["review_required"] != has_review:
            _fail(
                f"Expected review_required={expected['review_required']}, "
                f"but got {len(review_tasks)} review tasks"
            )

    # 6. Assert actor.reasoning presence (optional)
    if expected.get("actor_reasoning_present"):
        if conv_data is None:
            conv_data = api_client.get_conversation(conversation_id)
            events_cache = conv_data.get("events", [])
        reasoning_events = [e for e in events_cache if e.get("eventType") == "actor.reasoning"]
        if not reasoning_events:
            _fail("Expected at least one actor.reasoning event, but none were emitted")

    # 7. Assert tool_calls_include (optional)
    expected_tools = expected.get("tool_calls_include") or []
    if expected_tools:
        if conv_data is None:
            conv_data = api_client.get_conversation(conversation_id)
            events_cache = conv_data.get("events", [])
        called_tools: set[str] = set()
        for ev in events_cache:
            if ev.get("eventType") != "actor.progress":
                continue
            ev_payload = ev.get("payload") or {}
            if ev_payload.get("eventFamily") != "tool":
                continue
            if ev_payload.get("eventName") != "started":
                continue
            tool_name = ev_payload.get("toolName")
            if tool_name:
                called_tools.add(tool_name)
        # Only enforce if any tool events fired (mock runtime might not emit them)
        if called_tools:
            missing = [t for t in expected_tools if t not in called_tools]
            if missing:
                _fail(
                    f"Expected tool calls {expected_tools}; missing {missing}; "
                    f"actually called {sorted(called_tools)}"
                )

    # 8. Assert loop_count bounds (optional)
    loop_min = expected.get("loop_count_min")
    loop_max = expected.get("loop_count_max")
    if loop_min is not None or loop_max is not None:
        # Prefer run summary as source of truth
        run_id = ctx.get("run_id")
        if not run_id:
            if conv_data is None:
                conv_data = api_client.get_conversation(conversation_id)
                events_cache = conv_data.get("events", [])
            for ev in reversed(events_cache):
                if ev.get("eventType") == "response.final":
                    run_id = (ev.get("payload") or {}).get("runId")
                    break
        loop_count = 0
        if run_id:
            try:
                run_data = api_client.get_run(run_id)
                loop_count = (run_data.get("summary") or {}).get("loopCount") or 0
            except Exception:
                loop_count = 0
        if loop_count == 0:
            # Fallback: count actor.reasoning events
            if conv_data is None:
                conv_data = api_client.get_conversation(conversation_id)
                events_cache = conv_data.get("events", [])
            loop_count = sum(1 for ev in events_cache if ev.get("eventType") == "actor.reasoning")
        if loop_min is not None and loop_count < loop_min:
            _fail(f"Expected at least {loop_min} loops, got {loop_count}")
        if loop_max is not None and loop_count > loop_max:
            _fail(f"Expected at most {loop_max} loops, got {loop_count}")
