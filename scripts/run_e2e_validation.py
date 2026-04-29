from __future__ import annotations

import argparse
import json
import os
import queue
import threading
import time
import uuid
from typing import Any
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from run_fixture_scenarios import (
    HttpResult,
    api_key_header,
    create_conversation,
    load_scenarios,
    raw_request,
    read_env_file_value,
    run_scenario,
    send_message,
)

AI_SERVICE_SECRET = (
    os.getenv("POC_AI_SERVICE_SECRET")
    or os.getenv("AI_SERVICE_SECRET")
    or read_env_file_value("AI_SERVICE_SECRET")
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run end-to-end POC validation")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=12.0)
    args = parser.parse_args()

    checks = [
        ("health", lambda: validate_health(args.api_base)),
        ("fixtures", lambda: validate_fixture_suite(args.api_base, args.timeout)),
        ("sse-stream", lambda: validate_sse_stream(args.api_base, args.timeout)),
        ("sse-replay", lambda: validate_sse_replay(args.api_base, args.timeout)),
        ("external-ai-event", lambda: validate_external_ai_event(args.api_base, args.timeout)),
    ]

    failed = 0
    for name, check in checks:
        try:
            check()
            print(f"PASS {name}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {name}: {exc}")

    return 1 if failed else 0


def validate_health(api_base: str) -> None:
    response = raw_request(api_base, "/health", "GET", b"")
    if response.status != 200:
        raise AssertionError(f"expected health HTTP 200, got {response.status}")
    body = response.json()
    if body.get("status") != "ok":
        raise AssertionError(f"unexpected health body: {body}")


def validate_fixture_suite(api_base: str, timeout: float) -> None:
    for scenario in load_scenarios(None):
        run_scenario(api_base, scenario, timeout)


def validate_sse_stream(api_base: str, timeout: float) -> None:
    scenario = {
        "id": "e2e-sse-stream",
        "conversation": {
            "channel": "web_chat",
            "userSessionId": "e2e-sse-stream",
            "metadata": {
                "locale": "pt-BR",
                "timezone": "America/Sao_Paulo",
            },
        },
        "message": {
            "text": "Validacao ponta a ponta do stream SSE.",
            "metadata": {
                "locale": "pt-BR",
            },
            "attachments": [],
        },
    }
    request_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"multi-agent-bench:{scenario['id']}"))
    conversation = create_conversation(api_base, scenario, request_id)
    conversation_id = conversation["conversationId"]
    events: queue.Queue[dict[str, Any]] = queue.Queue()
    errors: queue.Queue[Exception] = queue.Queue()
    stop_event = threading.Event()

    thread = threading.Thread(
        target=collect_sse_events,
        args=(api_base, conversation_id, request_id, events, errors, stop_event, timeout),
        daemon=True,
    )
    thread.start()
    time.sleep(0.25)

    response = send_message(api_base, conversation_id, scenario, request_id)
    if response.status != 202:
        raise AssertionError(f"expected message HTTP 202, got {response.status}")

    collected = wait_for_stream_completion(events, errors, timeout)
    stop_event.set()
    thread.join(timeout=2)

    event_types = [event["eventType"] for event in collected]
    for event_type in ["message.received", "processing.started", "response.final", "processing.completed"]:
        if event_type not in event_types:
            raise AssertionError(f"missing streamed event {event_type}")

    detail = poll_detail(api_base, conversation_id, timeout)
    persisted_event_ids = {event["id"] for event in detail["events"]}
    streamed_event_ids = {event["id"] for event in collected}
    if not streamed_event_ids.issubset(persisted_event_ids):
        raise AssertionError("streamed events are not all persisted")
    if not any(message["direction"] == "outbound" for message in detail["messages"]):
        raise AssertionError("conversation history does not include outbound response")
    if len(detail["messages"]) < 2:
        raise AssertionError("conversation refresh did not return inbound and outbound messages")


def validate_sse_replay(api_base: str, timeout: float) -> None:
    scenario = {
        "id": "e2e-sse-replay",
        "conversation": {
            "channel": "web_chat",
            "userSessionId": "e2e-sse-replay",
            "metadata": {
                "locale": "pt-BR",
                "timezone": "America/Sao_Paulo",
            },
        },
        "message": {
            "text": "Validacao de replay SSE.",
            "metadata": {
                "locale": "pt-BR",
            },
            "attachments": [],
        },
    }
    request_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"multi-agent-bench:{scenario['id']}"))
    conversation = create_conversation(api_base, scenario, request_id)
    response = send_message(api_base, conversation["conversationId"], scenario, request_id)
    if response.status != 202:
        raise AssertionError(f"expected message HTTP 202, got {response.status}")

    detail = poll_detail(api_base, conversation["conversationId"], timeout)
    first_event_id = detail["events"][0]["id"]

    events: queue.Queue[dict[str, Any]] = queue.Queue()
    errors: queue.Queue[Exception] = queue.Queue()
    stop_event = threading.Event()
    thread = threading.Thread(
        target=collect_sse_events,
        args=(
            api_base,
            conversation["conversationId"],
            request_id,
            events,
            errors,
            stop_event,
            timeout,
            first_event_id,
        ),
        daemon=True,
    )
    thread.start()
    collected = wait_for_stream_completion(events, errors, timeout)
    stop_event.set()
    thread.join(timeout=2)

    event_types = [event["eventType"] for event in collected]
    if "response.final" not in event_types:
        raise AssertionError("SSE replay did not include response.final")
    if first_event_id in {event["id"] for event in collected}:
        raise AssertionError("SSE replay repeated the cursor event")


def validate_external_ai_event(api_base: str, timeout: float) -> None:
    scenario = {
        "id": "e2e-external-ai-event",
        "conversation": {
            "channel": "web_chat",
            "userSessionId": "e2e-external-ai-event",
            "metadata": {
                "locale": "pt-BR",
                "timezone": "America/Sao_Paulo",
            },
        },
        "message": {
            "text": "Validacao de evento externo de IA.",
            "metadata": {
                "locale": "pt-BR",
            },
            "attachments": [],
        },
    }
    request_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"multi-agent-bench:{scenario['id']}"))
    conversation = create_conversation(api_base, scenario, request_id)
    message_response = send_message(api_base, conversation["conversationId"], scenario, request_id)
    if message_response.status != 202:
        raise AssertionError(f"expected message HTTP 202, got {message_response.status}")
    message = message_response.json()

    external_event_id = f"e2e-{uuid.uuid4()}"
    payload = {
        "conversationId": conversation["conversationId"],
        "messageId": message["messageId"],
        "runId": message["runId"],
        "eventType": "actor.progress",
        "actorName": "external_ai_service",
        "correlationId": message["correlationId"],
        "status": "running",
        "externalEventId": external_event_id,
        "source": "ai_service",
        "payload": {
            "step": "e2e_validation",
            "message": "External AI validation event",
            "progressPercent": 40,
        },
    }
    first = post_ai_event(api_base, payload)
    if first.status != 202:
        raise AssertionError(f"expected external event HTTP 202, got {first.status}")
    second = post_ai_event(api_base, payload)
    if second.status != 202:
        raise AssertionError(f"expected idempotent external event HTTP 202, got {second.status}")
    if first.json()["id"] != second.json()["id"]:
        raise AssertionError("external event idempotency returned different event IDs")

    detail = poll_detail(api_base, conversation["conversationId"], timeout)
    if not any(
        event.get("payload", {}).get("externalEventId") == external_event_id
        and event.get("payload", {}).get("runId") == message["runId"]
        for event in detail["events"]
    ):
        raise AssertionError("external AI event was not persisted with run linkage")


def collect_sse_events(
    api_base: str,
    conversation_id: str,
    request_id: str,
    events: queue.Queue[dict[str, Any]],
    errors: queue.Queue[Exception],
    stop_event: threading.Event,
    timeout: float,
    last_event_id: str | None = None,
) -> None:
    path = f"conversations/{conversation_id}/events/stream"
    if last_event_id:
        path = f"{path}?lastEventId={last_event_id}"
    request = Request(
        urljoin(
            api_base.rstrip("/") + "/",
            path,
        ),
        headers={
            "Accept": "text/event-stream",
            "X-Request-ID": request_id,
            **api_key_header(),
        },
    )
    deadline = time.monotonic() + timeout
    try:
        with urlopen(request, timeout=timeout) as response:
            event_name: str | None = None
            data_lines: list[str] = []
            while not stop_event.is_set() and time.monotonic() < deadline:
                raw_line = response.readline()
                if not raw_line:
                    break
                line = raw_line.decode("utf-8").rstrip("\r\n")
                if not line:
                    if event_name == "processing.event" and data_lines:
                        event = json.loads("\n".join(data_lines))
                        events.put(event)
                        if event.get("eventType") == "processing.completed":
                            return
                    event_name = None
                    data_lines = []
                    continue
                if line.startswith("event:"):
                    event_name = line.removeprefix("event:").strip()
                elif line.startswith("data:"):
                    data_lines.append(line.removeprefix("data:").strip())
    except (URLError, TimeoutError, OSError) as exc:
        if not stop_event.is_set():
            errors.put(exc)


def wait_for_stream_completion(
    events: queue.Queue[dict[str, Any]],
    errors: queue.Queue[Exception],
    timeout: float,
) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not errors.empty():
            raise errors.get()
        try:
            event = events.get(timeout=0.25)
        except queue.Empty:
            continue
        collected.append(event)
        if event.get("eventType") == "processing.completed":
            return collected
    raise AssertionError(f"timed out waiting for processing.completed; got {len(collected)} events")


def poll_detail(api_base: str, conversation_id: str, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_detail: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        response = raw_request(api_base, f"/conversations/{conversation_id}", "GET", b"")
        if response.status != 200:
            raise AssertionError(f"conversation detail failed with HTTP {response.status}")
        last_detail = response.json()
        if any(event["eventType"] == "processing.completed" for event in last_detail["events"]):
            return last_detail
        time.sleep(0.25)
    raise AssertionError(f"timed out waiting for persisted history; last detail: {last_detail}")


def post_ai_event(api_base: str, payload: dict[str, Any]) -> HttpResult:
    headers = {
        "Content-Type": "application/json",
        **api_key_header(),
        **ai_service_secret_header(),
    }
    return raw_request(
        api_base,
        "/integrations/ai/events",
        "POST",
        json.dumps(payload).encode("utf-8"),
        headers=headers,
    )


def ai_service_secret_header() -> dict[str, str]:
    return {"X-AI-Service-Secret": AI_SERVICE_SECRET} if AI_SERVICE_SECRET else {}


if __name__ == "__main__":
    raise SystemExit(main())
