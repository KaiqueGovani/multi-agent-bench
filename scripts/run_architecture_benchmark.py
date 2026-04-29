from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from run_fixture_scenarios import (
    create_conversation,
    load_scenarios,
    poll_conversation,
    send_message,
)


ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / "var" / "reports" / "runtime" / "T11"
ARCHITECTURES = [
    "centralized_orchestration",
    "structured_workflow",
    "decentralized_swarm",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run architecture benchmark for multi-agent-bench")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=16.0)
    parser.add_argument("--scenario", action="append")
    args = parser.parse_args()

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target_dir = REPORT_ROOT / timestamp
    target_dir.mkdir(parents=True, exist_ok=True)

    scenarios = load_scenarios(args.scenario)
    results: list[dict[str, Any]] = []
    failed = 0

    for architecture in ARCHITECTURES:
        for scenario in scenarios:
            scenario_copy = json.loads(json.dumps(scenario))
            scenario_copy["conversation"]["metadata"]["architectureMode"] = architecture
            scenario_copy["message"]["metadata"]["architectureMode"] = architecture
            request_id = f"benchmark-{architecture}-{scenario_copy['id']}"
            try:
                conversation = create_conversation(args.api_base, scenario_copy, request_id)
                response = send_message(
                    args.api_base,
                    conversation["conversationId"],
                    scenario_copy,
                    request_id,
                )
                detail = None
                if response.status == 202:
                    detail = poll_conversation(
                        args.api_base,
                        conversation["conversationId"],
                        scenario_copy["expected"],
                        args.timeout,
                    )
                result = summarize_result(architecture, scenario_copy, response.status, detail)
                results.append(result)
                print(f"PASS {architecture} {scenario_copy['id']}")
            except Exception as exc:
                failed += 1
                results.append(
                    {
                        "architecture": architecture,
                        "scenarioId": scenario_copy["id"],
                        "status": "failed",
                        "error": str(exc),
                    }
                )
                print(f"FAIL {architecture} {scenario_copy['id']}: {exc}")

    (target_dir / "benchmark-results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    (target_dir / "final-benchmark-report.md").write_text(
        render_markdown_report(results),
        encoding="utf-8",
    )
    return 1 if failed else 0


def summarize_result(
    architecture: str,
    scenario: dict[str, Any],
    status_code: int,
    detail: dict[str, Any] | None,
) -> dict[str, Any]:
    latest_run = (detail or {}).get("runs", [{}])[-1] if detail else {}
    return {
        "architecture": architecture,
        "scenarioId": scenario["id"],
        "status": "passed" if status_code == 202 else "unexpected_http_status",
        "httpStatus": status_code,
        "runId": latest_run.get("id"),
        "runStatus": latest_run.get("status"),
        "traceId": latest_run.get("traceId"),
        "totalDurationMs": latest_run.get("totalDurationMs"),
        "toolCallCount": (latest_run.get("summary") or {}).get("toolCallCount"),
        "loopCount": (latest_run.get("summary") or {}).get("loopCount"),
        "humanReviewRequired": latest_run.get("humanReviewRequired"),
    }


def render_markdown_report(results: list[dict[str, Any]]) -> str:
    lines = [
        "# Final Benchmark Report",
        "",
        f"Generated at: {datetime.now(UTC).isoformat()}",
        "",
        "| Architecture | Scenario | Status | Run Status | Duration (ms) | Tool Calls | Loops | Review |",
        "|---|---|---|---|---:|---:|---:|---|",
    ]
    for result in results:
        lines.append(
            "| {architecture} | {scenarioId} | {status} | {runStatus} | {totalDurationMs} | {toolCallCount} | {loopCount} | {humanReviewRequired} |".format(
                architecture=result.get("architecture", "n/a"),
                scenarioId=result.get("scenarioId", "n/a"),
                status=result.get("status", "n/a"),
                runStatus=result.get("runStatus", "n/a"),
                totalDurationMs=result.get("totalDurationMs", "n/a"),
                toolCallCount=result.get("toolCallCount", "n/a"),
                loopCount=result.get("loopCount", "n/a"),
                humanReviewRequired=result.get("humanReviewRequired", "n/a"),
            )
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
