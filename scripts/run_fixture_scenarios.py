from __future__ import annotations

import argparse
import base64
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
FIXTURES_ROOT = ROOT / "packages" / "test-fixtures"
SCENARIOS_ROOT = FIXTURES_ROOT / "scenarios"


@dataclass(frozen=True)
class HttpResult:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run POC fixture scenarios")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--scenario", action="append", help="Scenario id to run")
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()

    scenarios = load_scenarios(args.scenario)
    failed = 0
    for scenario in scenarios:
        try:
            run_scenario(args.api_base, scenario, args.timeout)
            print(f"PASS {scenario['id']}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {scenario['id']}: {exc}")

    return 1 if failed else 0


def load_scenarios(selected_ids: list[str] | None) -> list[dict[str, Any]]:
    scenarios = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(SCENARIOS_ROOT.glob("*.json"))
    ]
    if not selected_ids:
        return scenarios

    selected = set(selected_ids)
    filtered = [scenario for scenario in scenarios if scenario["id"] in selected]
    missing = selected - {scenario["id"] for scenario in filtered}
    if missing:
        raise ValueError(f"Unknown scenarios: {', '.join(sorted(missing))}")
    return filtered


def run_scenario(api_base: str, scenario: dict[str, Any], timeout: float) -> None:
    request_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"multi-agent-bench:{scenario['id']}"))
    conversation = create_conversation(api_base, scenario, request_id)
    response = send_message(api_base, conversation["conversationId"], scenario, request_id)
    expected = scenario["expected"]

    if response.status != expected["httpStatus"]:
        raise AssertionError(
            f"expected HTTP {expected['httpStatus']}, got {response.status}: "
            f"{response.body.decode('utf-8', errors='replace')}"
        )

    if expected["httpStatus"] != 202:
        body = response.body.decode("utf-8", errors="replace")
        expected_error = expected.get("errorContains")
        if expected_error and expected_error not in body:
            raise AssertionError(f"expected error containing {expected_error!r}, got {body!r}")
        return

    detail = poll_conversation(api_base, conversation["conversationId"], expected, timeout)
    validate_detail(detail, expected)


def create_conversation(
    api_base: str,
    scenario: dict[str, Any],
    request_id: str,
) -> dict[str, Any]:
    result = json_request(
        api_base,
        "/conversations",
        "POST",
        scenario["conversation"],
        headers={"X-Request-ID": request_id},
    )
    if result.status != 201:
        raise AssertionError(f"conversation creation failed with HTTP {result.status}")
    return result.json()


def send_message(
    api_base: str,
    conversation_id: str,
    scenario: dict[str, Any],
    request_id: str,
) -> HttpResult:
    body, content_type = build_message_multipart(conversation_id, scenario)
    return raw_request(
        api_base,
        "/messages",
        "POST",
        body,
        headers={
            "Content-Type": content_type,
            "X-Request-ID": request_id,
        },
    )


def build_message_multipart(
    conversation_id: str,
    scenario: dict[str, Any],
) -> tuple[bytes, str]:
    boundary = f"fixture-{uuid.uuid4().hex}"
    parts: list[bytes] = []
    message = scenario["message"]

    add_form_field(parts, boundary, "conversationId", conversation_id)
    if message.get("text"):
        add_form_field(parts, boundary, "text", message["text"])
    add_form_field(parts, boundary, "metadata_json", json.dumps(message.get("metadata", {})))

    scenario_dir = SCENARIOS_ROOT
    for attachment in message.get("attachments", []):
        content = read_attachment_content(scenario_dir, attachment)
        add_file_field(
            parts,
            boundary,
            attachment.get("fieldName", "files"),
            attachment["filename"],
            attachment["mimeType"],
            content,
        )

    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def add_form_field(parts: list[bytes], boundary: str, name: str, value: str) -> None:
    parts.append(f"--{boundary}\r\n".encode("utf-8"))
    parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
    parts.append(value.encode("utf-8"))
    parts.append(b"\r\n")


def add_file_field(
    parts: list[bytes],
    boundary: str,
    name: str,
    filename: str,
    mime_type: str,
    content: bytes,
) -> None:
    parts.append(f"--{boundary}\r\n".encode("utf-8"))
    parts.append(
        (
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8")
    )
    parts.append(content)
    parts.append(b"\r\n")


def read_attachment_content(scenario_dir: Path, attachment: dict[str, Any]) -> bytes:
    path = (scenario_dir / attachment["path"]).resolve()
    if attachment["source"] == "base64":
        return base64.b64decode(path.read_text(encoding="utf-8").strip())
    return path.read_bytes()


def poll_conversation(
    api_base: str,
    conversation_id: str,
    expected: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_detail: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        result = raw_request(api_base, f"/conversations/{conversation_id}", "GET", b"")
        if result.status != 200:
            raise AssertionError(f"conversation detail failed with HTTP {result.status}")
        last_detail = result.json()
        if expectations_are_ready(last_detail, expected):
            return last_detail
        time.sleep(0.25)
    raise AssertionError(f"timed out waiting for expected events; last detail: {last_detail}")


def expectations_are_ready(detail: dict[str, Any], expected: dict[str, Any]) -> bool:
    event_types = {event["eventType"] for event in detail["events"]}
    required_events = set(expected.get("eventTypes", []))
    if not required_events.issubset(event_types):
        return False
    if expected.get("reviewRequired") and not detail.get("reviewTasks"):
        return False
    return any(message["direction"] == "outbound" for message in detail["messages"])


def validate_detail(detail: dict[str, Any], expected: dict[str, Any]) -> None:
    events = detail["events"]
    route = expected.get("route")
    if route and not any(event.get("payload", {}).get("route") == route for event in events):
        raise AssertionError(f"expected route {route!r}")

    actor = expected.get("actor")
    if actor and not any(event.get("actorName") == actor for event in events):
        raise AssertionError(f"expected actor {actor!r}")

    if expected.get("reviewRequired"):
        if detail["conversation"]["status"] != expected.get("conversationStatus"):
            raise AssertionError("conversation was not marked for human review")
        task_statuses = {task["status"] for task in detail.get("reviewTasks", [])}
        if expected.get("reviewTaskStatus") not in task_statuses:
            raise AssertionError("expected review task was not created")

    final_events = [event for event in events if event["eventType"] == "response.final"]
    if not final_events:
        raise AssertionError("missing response.final event")
    review_flag = final_events[-1].get("payload", {}).get("reviewRequired")
    if review_flag is not expected.get("reviewRequired", False):
        raise AssertionError("response.final reviewRequired flag does not match scenario")

    attachment_dimensions = expected.get("attachmentDimensions")
    if attachment_dimensions:
        matching_attachments = [
            attachment
            for attachment in detail.get("attachments", [])
            if attachment.get("width") == attachment_dimensions["width"]
            and attachment.get("height") == attachment_dimensions["height"]
        ]
        if not matching_attachments:
            raise AssertionError(
                f"expected attachment dimensions {attachment_dimensions!r}"
            )


def json_request(
    api_base: str,
    path: str,
    method: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> HttpResult:
    return raw_request(
        api_base,
        path,
        method,
        json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
    )


def raw_request(
    api_base: str,
    path: str,
    method: str,
    body: bytes,
    headers: dict[str, str] | None = None,
) -> HttpResult:
    request = Request(
        urljoin(api_base.rstrip("/") + "/", path.lstrip("/")),
        data=body if method != "GET" else None,
        method=method,
        headers=headers or {},
    )
    try:
        with urlopen(request, timeout=10) as response:
            return HttpResult(
                status=response.status,
                headers=dict(response.headers.items()),
                body=response.read(),
            )
    except HTTPError as exc:
        return HttpResult(
            status=exc.code,
            headers=dict(exc.headers.items()),
            body=exc.read(),
        )


if __name__ == "__main__":
    raise SystemExit(main())
