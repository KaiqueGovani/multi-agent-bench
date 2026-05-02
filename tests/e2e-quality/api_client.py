"""Thin HTTP + SSE client for the Multi-Agent Bench API."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path

import httpx


class E2EClient:
    """Sync client that talks to the chat-api following the exact wire contract."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0):
        self._http = httpx.Client(
            base_url=base_url,
            headers={"X-API-Key": api_key},
            timeout=timeout,
        )

    # -- context manager --------------------------------------------------

    def __enter__(self) -> "E2EClient":
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self._http.close()

    # -- endpoints --------------------------------------------------------

    def create_conversation(self, metadata: dict | None = None) -> str:
        resp = self._http.post(
            "/conversations",
            json={"channel": "web_chat", "userSessionId": None, "metadata": metadata or {}},
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        return resp.json()["conversationId"]

    def send_message(
        self,
        conversation_id: str,
        text: str,
        metadata: dict | None = None,
        *,
        attachments: list[tuple[Path, str]] | None = None,
        expected_status: int = 202,
    ) -> dict:
        """Send a user message. Optionally upload files via multipart.

        If *attachments* is provided, each tuple is ``(path, mime_type)``.
        When *path* ends with ``.base64``, the file content is base64-decoded
        before upload so we can store small PNG/PDF fixtures as text-friendly
        ``.base64`` sidecars.  Otherwise, raw bytes are sent.

        *expected_status* is asserted against the HTTP response status.  For
        error scenarios (e.g. 400), the returned dict is
        ``{"error": <response text>, "status_code": <code>}`` instead of the
        parsed JSON body.
        """
        data = {
            "conversationId": conversation_id,
            "text": text,
            "metadata_json": json.dumps(metadata or {}),
        }

        files = None
        if attachments:
            files = []
            for att_path, mime_type in attachments:
                if att_path.suffix.lower() == ".base64":
                    content = base64.b64decode(att_path.read_text().strip())
                    filename = att_path.stem  # strips .base64
                else:
                    content = att_path.read_bytes()
                    filename = att_path.name
                files.append(("files", (filename, content, mime_type)))

        resp = self._http.post("/messages", data=data, files=files)
        assert resp.status_code == expected_status, (
            f"Expected {expected_status}, got {resp.status_code}: {resp.text}"
        )
        if resp.status_code >= 400:
            return {"error": resp.text, "status_code": resp.status_code}
        return resp.json()

    def get_conversation(self, conversation_id: str) -> dict:
        resp = self._http.get(f"/conversations/{conversation_id}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        return resp.json()

    def get_run(self, run_id: str) -> dict:
        """Fetch a run record by ID. Returns the full JSON object including summary and experiment."""
        resp = self._http.get(f"/runs/{run_id}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        return resp.json()

    # -- SSE stream -------------------------------------------------------

    def wait_for_event(
        self,
        conversation_id: str,
        event_type: str,
        timeout: float,
        *,
        since_event_id: str | None = None,
        match: callable | None = None,
    ) -> dict:
        """Block until an SSE event with the given eventType arrives, or raise TimeoutError."""
        params: dict = {}
        if since_event_id:
            params["lastEventId"] = since_event_id

        deadline = time.monotonic() + timeout

        with self._http.stream(
            "GET",
            f"/conversations/{conversation_id}/events/stream",
            params=params,
            headers={"Accept": "text/event-stream"},
            timeout=httpx.Timeout(timeout + 5, connect=10),
        ) as stream:
            current_event = ""
            current_data = ""
            current_id = ""

            for line in stream.iter_lines():
                if time.monotonic() > deadline:
                    break

                if line.startswith("event:"):
                    current_event = line[len("event:"):].strip()
                elif line.startswith("id:"):
                    current_id = line[len("id:"):].strip()
                elif line.startswith("data:"):
                    current_data = line[len("data:"):].strip()
                elif line == "":
                    # End of frame — process it
                    if current_event == "heartbeat" or not current_data:
                        current_event = current_data = current_id = ""
                        continue

                    try:
                        payload = json.loads(current_data)
                    except json.JSONDecodeError:
                        current_event = current_data = current_id = ""
                        continue

                    if payload.get("eventType") == event_type:
                        if match is None or match(payload):
                            return payload

                    current_event = current_data = current_id = ""

        raise TimeoutError(
            f"Timed out after {timeout}s waiting for eventType={event_type!r} "
            f"on conversation {conversation_id}"
        )
