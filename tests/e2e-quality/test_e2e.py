"""E2E scenario tests — driven by YAML files in scenarios/."""

from __future__ import annotations

import unicodedata

import pytest

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
    conversation_id = api_client.create_conversation(metadata=conv_meta)
    ctx["conversation_id"] = conversation_id
    assert conversation_id, "conversationId must be a non-empty string"

    # 2. Send message
    msg_meta = {"architectureMode": architecture, "locale": "pt-BR", "scenarioId": case["id"]}
    msg_resp = api_client.send_message(conversation_id, case["input"]["text"], metadata=msg_meta)
    ctx["correlation_id"] = msg_resp.get("correlationId")
    ctx["run_id"] = msg_resp.get("runId")

    def _fail(reason: str):
        pytest.fail(f"{reason} | conv={ctx['conversation_id']} corr={ctx['correlation_id']}")

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

        # Route assertion — check response text, payload.route, or payload.response.route
        route = expected["route"]
        nested_response = payload.get("response") if isinstance(payload.get("response"), dict) else {}
        route_found = (
            _normalize(route) in norm_text
            or payload.get("route") == route
            or nested_response.get("route") == route
        )
        if not route_found:
            _fail(
                f"Expected route '{route}' not found in response text or payload. "
                f"text={response_text!r}"
            )

        # final_actor assertion (optional)
        expected_final_actor = expected.get("final_actor")
        if expected_final_actor:
            actual_final_actor = payload.get("finalActor")
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
        conv_data = api_client.get_conversation(conversation_id)
        review_tasks = conv_data.get("reviewTasks", [])
        has_review = len(review_tasks) > 0
        if expected["review_required"] != has_review:
            _fail(
                f"Expected review_required={expected['review_required']}, "
                f"but got {len(review_tasks)} review tasks"
            )

    # 6. Assert actor.reasoning presence (optional)
    if expected.get("actor_reasoning_present"):
        conv_data = api_client.get_conversation(conversation_id)
        events = conv_data.get("events", [])
        reasoning_events = [e for e in events if e.get("eventType") == "actor.reasoning"]
        if not reasoning_events:
            _fail("Expected at least one actor.reasoning event, but none were emitted")
