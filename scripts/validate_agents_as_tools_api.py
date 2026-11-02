"""Real, sequential API integration checks; separate from the scientific benchmark.

Use the API virtualenv. API_KEY is read from the process environment, never arguments.
The output directory is private and refuses reuse so first attempts remain intact.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import time
import unicodedata
from typing import Any

import httpx


CASES = [
    {"id": "faq", "text": "Qual é o horário de funcionamento da farmácia?", "roles": ["faq"], "tools": ["faq_lookup"]},
    {"id": "stock", "text": "Vocês têm dipirona em estoque?", "roles": ["stock"], "tools": ["stock_lookup"]},
    {"id": "attachments", "text": "Recebi este arquivo sintético. Registre os metadados do anexo e explique os limites de leitura.", "attachment": True, "roles": ["attachments"], "tools": ["attachment_intake"]},
    {"id": "multiple-sources", "text": "Qual o horário da farmácia e vocês têm dipirona em estoque? Registre também os metadados deste anexo sintético.", "attachment": True, "roles": ["faq", "stock", "attachments"], "tools": ["faq_lookup", "stock_lookup", "attachment_intake"]},
]
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a2ioAAAAASUVORK5CYII=")


def sanitized(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "[REDACTED]" if any(token in key.lower() for token in ("apikey", "secret", "authorization", "bearer", "credential")) else sanitized(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitized(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"([?&]apiKey=)[^&\s]+", r"\1[REDACTED]", value)
    return value


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(sanitized(data), ensure_ascii=False, indent=2) + "\n")
    path.chmod(0o600)


def decode_tool_result(result: Any) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None
    if "status" not in result:
        return result
    if result["status"] != "success":
        return None
    for block in result.get("content", []):
        if isinstance(block.get("json"), dict):
            return block["json"]
        if "text" in block:
            try:
                parsed = json.loads(block["text"])
                if isinstance(parsed, dict):
                    return parsed
            except (ValueError, TypeError):
                pass
    return None


def source_matches(tool: str, arguments: dict[str, Any], result: dict[str, Any] | None) -> bool:
    if result is None:
        return False
    query = "".join(c for c in unicodedata.normalize("NFKD", json.dumps(arguments, ensure_ascii=False).lower()) if not unicodedata.combining(c))
    if tool == "stock_lookup":
        return "dipirona" in query and result.get("product") == "dipirona" and result.get("quantity") == 17
    if tool == "faq_lookup":
        return any(word in query for word in ("horario", "funcionamento", "abre", "fecha")) and result.get("topic") == "horario" and bool(result.get("answer"))
    if tool == "attachment_intake":
        uploaded = arguments.get("attachments")
        returned = result.get("attachments")
        if not isinstance(uploaded, list) or not uploaded or not isinstance(returned, list):
            return False
        keys = ("attachmentId", "originalFilename", "mimeType", "sizeBytes")
        return all(any(all(descriptor.get(key) == item.get(key) for key in keys) for item in returned) for descriptor in uploaded)
    return False


def verify(execution: dict[str, Any], detail: dict[str, Any], case: dict[str, Any], protocol: str) -> dict[str, Any]:
    events = execution["executionEvents"]
    run = execution["run"]
    failures = []
    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)
    check(run["status"] in ("completed", "human_review_required"), "terminal successful technical status")
    check(run["experiment"].get("comparisonProtocol") == protocol, "correct comparison protocol dispatch")
    agents = [event for event in events if event["eventFamily"] == "agent" and event["eventName"] == "started"]
    roles = {event.get("actorName") for event in agents}
    check("supervisor" in roles and set(case["roles"]).issubset(roles), "requested real agent roles")
    models = [event for event in events if event["eventFamily"] == "model" and event["eventName"] == "completed" and event["status"] == "completed"]
    check(set(case["roles"]).issubset({event.get("actorName") for event in models}), "physical model completion per specialist")
    domains = [event for event in events if event["eventFamily"] == "tool" and event["eventName"] == "completed" and event["status"] == "completed" and event.get("toolName") in case["tools"] and event.get("payload", {}).get("result") is not None]
    check(set(case["tools"]).issubset({event.get("toolName") for event in domains}), "completed required domain queries and results")
    matched_sources = set()
    for domain in domains:
        tool_id = domain.get("payload", {}).get("toolCallId")
        starts = [event for event in events if event["eventFamily"] == "tool" and event["eventName"] == "started" and event.get("toolName") == domain.get("toolName") and event.get("payload", {}).get("toolCallId") == tool_id]
        check(len(starts) == 1 and bool(starts[0].get("payload", {}).get("input")), "domain completion links to recorded arguments")
        if starts:
            arguments = starts[0].get("payload", {}).get("input", {})
            if source_matches(domain["toolName"], arguments, decode_tool_result(domain["payload"]["result"])):
                matched_sources.add(domain["toolName"])
    # Extra genuine consultations remain behavior to measure. They do not erase
    # the evidence from a correct consultation of each mandatory source.
    for tool in case["tools"]:
        check(tool in matched_sources, f"required source has matching recorded arguments and return: {tool}")
    check(not any(event.get("actorName") == "supervisor" and event.get("toolName") in ("faq_lookup", "stock_lookup", "attachment_intake") for event in events), "no direct supervisor domain access")
    supervisor_ids = {event["payload"].get("agentInvocationId", event["payload"].get("callId")) for event in agents if event.get("actorName") == "supervisor"}
    check(all(event["payload"].get("parentAgentInvocationId") in supervisor_ids and event["payload"].get("parentCallId") for event in agents if event.get("actorName") in case["roles"]), "specialist parent IDs link to supervisor tools")
    returns = [event for event in events if event["eventFamily"] == "communication" and event.get("payload", {}).get("to") == "supervisor"]
    check(set(case["roles"]).issubset({event.get("actorName") for event in returns}), "specialist results returned to supervisor")
    final = [event for event in events if event["eventFamily"] == "response" and event["eventName"] == "final"]
    check(len(final) == 1 and final[0].get("actorName") == "supervisor", "supervisor final authority")
    if final and returns:
        check(max(event["sequenceNo"] for event in returns) < final[0]["sequenceNo"], "returns precede final answer")
    ids = [event["id"] for event in events]
    check(len(ids) == len(set(ids)), "unique persisted event IDs")
    check(any(message["direction"] == "outbound" and message.get("metadata", {}).get("runtimeRunId") == run["id"] for message in detail["messages"]), "outbound response persisted for run")
    check(execution.get("projection", {}).get("runStatus") == run["status"], "terminal projection persisted")
    return {"passed": not failures, "failures": failures, "agents": sorted(roles), "model_completions": len(models), "required_domain_completions": len(domains), "event_count": len(events), "summary": run.get("summary", {})}


def verify_sse_replay(client: httpx.Client, run_id: str, events: list[dict[str, Any]]) -> int:
    """Replay persisted execution events through the same SSE endpoint used by the UI."""
    expected_ids = {event["id"] for event in events}
    observed_ids: set[str] = set()
    if not expected_ids:
        raise AssertionError("Cannot verify an empty SSE execution trace")
    with client.stream("GET", f"/runs/{run_id}/execution/stream", params={"lastSequenceNo": 0}, timeout=30) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line.startswith("data:"):
                payload = json.loads(line.removeprefix("data:").strip())
                if "id" in payload:
                    observed_ids.add(payload["id"])
                if expected_ids.issubset(observed_ids):
                    break
    if observed_ids != expected_ids:
        raise AssertionError("SSE replay does not reconcile with persisted execution events")
    return len(observed_ids)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--protocol", default="architectural-comparison-v4.2")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=210)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    write_json(args.output / "cases-frozen.json", {"purpose": "API/UI engineering integration, not benchmark", "protocol": args.protocol, "cases": CASES, "attachment_sha256": hashlib.sha256(PNG).hexdigest()})
    headers = {"X-API-Key": os.environ["API_KEY"]} if os.environ.get("API_KEY") else {}
    records = []
    with httpx.Client(base_url=args.api_base, headers=headers, timeout=30) as client:
        for case in CASES:
            started = time.monotonic()
            conversation = client.post("/conversations", json={"channel": "web_chat", "metadata": {"architectureMode": "centralized_orchestration", "source": "agents-as-tools-integration", "synthetic": True}})
            conversation.raise_for_status()
            conversation_id = conversation.json()["conversationId"]
            write_json(args.output / f"{case['id']}-started.json", {"case": case, "conversationId": conversation_id})
            metadata = {"runtimeMode": "real", "architectureMode": "centralized_orchestration", "comparisonProtocol": args.protocol, "experimentId": "engineering-api-agents-as-tools", "scenarioId": f"synthetic-api-{case['id']}"}
            files = [("files", ("synthetic-metadata-only.png", PNG, "image/png"))] if case.get("attachment") else None
            message = client.post("/messages", data={"conversationId": conversation_id, "text": case["text"], "metadata_json": json.dumps(metadata)}, files=files)
            message.raise_for_status()
            run_id = message.json()["runId"]
            write_json(args.output / f"{case['id']}-accepted.json", message.json())
            deadline = time.monotonic() + args.timeout
            while True:
                response = client.get(f"/runs/{run_id}/execution")
                response.raise_for_status()
                execution = response.json()
                if execution["run"]["status"] in ("completed", "human_review_required", "failed", "cancelled"):
                    break
                if time.monotonic() >= deadline:
                    write_json(args.output / f"{case['id']}-execution-timeout.json", execution)
                    raise TimeoutError(f"Integration case {case['id']} did not finish; first attempt preserved")
                time.sleep(0.5)
            response = client.get(f"/conversations/{conversation_id}")
            response.raise_for_status()
            detail = response.json()
            write_json(args.output / f"{case['id']}-execution.json", execution)
            write_json(args.output / f"{case['id']}-conversation.json", detail)
            with (args.output / "events.jsonl").open("a") as stream:
                for event in execution["executionEvents"]:
                    stream.write(json.dumps(sanitized(event), ensure_ascii=False) + "\n")
            (args.output / "events.jsonl").chmod(0o600)
            checked = verify(execution, detail, case, args.protocol)
            checked["sse_replay_event_count"] = verify_sse_replay(client, run_id, execution["executionEvents"])
            record = {"caseId": case["id"], "conversationId": conversation_id, "runId": run_id, "api_to_terminal_latency_ms": (time.monotonic() - started) * 1000, **checked}
            records.append(record)
            write_json(args.output / "manifest.json", {"protocol": args.protocol, "transport": "API HTTP dispatch and persisted callbacks", "benchmark": False, "records": records})
            print(json.dumps({"caseId": case["id"], "runId": run_id, "passed": checked["passed"], "failures": checked["failures"]}), flush=True)
    return 0 if all(record["passed"] for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
