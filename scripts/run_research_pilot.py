#!/usr/bin/env python3
"""Sequential core-runtime pilot, immutable order, durable attempts and blind judging."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import fcntl
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import itertools
import platform
import signal
import shutil
import subprocess
import sys
import time
from threading import Event
from datetime import UTC, datetime
from dataclasses import asdict, replace
from uuid import UUID, uuid4, uuid5

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/agent-runtime"))
from dotenv import load_dotenv
load_dotenv(ROOT / "apps/agent-runtime/.env")
from app.architectures.comparison import ARCHITECTURES, PROTOCOL_VERSION, snapshot
from app.core.config import get_settings
from app.schemas.runtime import (RuntimeDispatchRequest, RunExperimentMetadata, RuntimeCallbackConfig,
                                RuntimeMessageSnapshot, RuntimeAttachmentDescriptor)
from app.services.execution import RuntimeExecutor

V43 = "architectural-comparison-v4.3"
V43_MAIN_COHORT = "definitive-synthetic40-v43"
V44 = "architectural-comparison-v4.4"


def dump(path, value):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.flush(); os.fsync(f.fileno())
    tmp.replace(path)


def append(path, value):
    with path.open("a") as f:
        f.write(json.dumps(value, ensure_ascii=False) + "\n")
        f.flush(); os.fsync(f.fileno())


def sha(value):
    return hashlib.sha256(value).hexdigest()


def code_hashes():
    files = list((ROOT / "apps/agent-runtime/app").rglob("*.py")) + list((ROOT / "scripts").glob("*research_pilot.py")) + list((ROOT / "scripts").glob("*automated_pilots.py")) + list((ROOT / "scripts").glob("*corrected_comparison.py"))
    return {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted(files)}


def dependency_versions():
    return {"python": platform.python_version(), **{
        package: importlib.metadata.version(package)
        for package in ("strands-agents", "boto3", "botocore", "pydantic")
    }}


def validate_environment(manifest):
    if manifest["sdk_version"] != importlib.metadata.version("strands-agents"):
        raise RuntimeError("SDK differs from frozen experiment")
    if "dependency_versions" in manifest and manifest["dependency_versions"] != dependency_versions():
        raise RuntimeError("Dependencies differ from frozen experiment")


def make_request(case, unit, experiment_id, protocol=PROTOCOL_VERSION):
    now = datetime.now(UTC)
    correlation = uuid4()
    def message(text, direction):
        return RuntimeMessageSnapshot(id=uuid4(), direction=direction, content_text=text,
            created_at_server=now, status="accepted", correlation_id=correlation)
    history = [message(m["text"], "inbound" if m["role"] == "customer" else "outbound") for m in case.get("history", [])]
    latest = message(case["text"], "inbound")
    latest.attachments = [RuntimeAttachmentDescriptor(
        attachment_id=uuid5(UUID("00000000-0000-0000-0000-000000000004"), case["id"]+a["filename"]), message_id=latest.id, original_filename=a["filename"],
        mime_type=a["mime_type"], size_bytes=a["size_bytes"], checksum="synthetic-metadata-only",
        retrieval_url="https://invalid.example/research-no-content",
    ) for a in case.get("attachments", [])]
    return RuntimeDispatchRequest(run_id=uuid4(), conversation_id=uuid4(), message_id=latest.id,
        correlation_id=correlation, architecture_mode=unit["architecture"],
        experiment=RunExperimentMetadata(architecture_key=unit["architecture"], experiment_id=experiment_id,
            scenario_id=case["id"], comparisonProtocol=protocol),
        latest_message=latest, conversation_history=history + [latest],
        callback=RuntimeCallbackConfig(base_url="http://unused.local"))


class LocalEvents:
    def __init__(self, path):
        self.path = path
        self.sequence = 0
    def emit_run_event(self, event):
        self.sequence += 1
        append(self.path, {"sequence": self.sequence, "recorded_at": datetime.now(UTC).isoformat(),
                          **event.model_dump(by_alias=True, mode="json")})


DOMAIN_TOOLS = {"faq_lookup", "stock_lookup", "attachment_intake"}
SPECIALIST_TOOLS = {"faq_specialist": "faq", "stock_specialist": "stock", "attachments_specialist": "attachments"}


def trace_measurements(events):
    """Reconcile physical requests once; aggregate SDK metrics are not additive."""
    model_starts = [e for e in events if e["eventFamily"] == "model" and e["eventName"] == "started"]
    model_ends = [e for e in events if e["eventFamily"] == "model" and e["eventName"] in {"completed", "failed"}]
    starts = {e["payload"]["callId"]: e for e in model_starts}
    ends = {e["payload"]["callId"]: e for e in model_ends}
    unique = len(starts) == len(model_starts) and len(ends) == len(model_ends)
    complete = bool(starts) and unique and starts.keys() == ends.keys() and all(
        e["eventName"] == "completed" and isinstance(e["payload"].get("usage"), dict)
        and all(e["payload"]["usage"].get(k) is not None for k in ("inputTokens", "outputTokens", "totalTokens"))
        for e in ends.values())
    agent_starts = [e for e in events if e["eventFamily"] == "agent" and e["eventName"] == "started"]
    tools = [e for e in events if e["eventFamily"] == "tool" and e["eventName"] == "started"]
    result = dict(agent_invocations=len(agent_starts), actual_agents=len({
        e["payload"].get("agentId") or e.get("actorName") for e in model_starts}),
        model_requests=len(starts), domain_tool_calls=sum(e.get("toolName") in DOMAIN_TOOLS for e in tools),
        coordination_tool_calls=sum(e.get("toolName") not in DOMAIN_TOOLS for e in tools),
        specialist_tool_invocations=sum(e.get("toolName") in SPECIALIST_TOOLS for e in tools),
        peer_delegations=sum(e["eventFamily"] == "handoff" and e["eventName"] == "requested" for e in events),
        explicit_messages=sum(e["eventFamily"] == "communication" and e["eventName"] == "message" for e in events),
        token_measurement_complete=complete, provider_call_ids_unique=unique)
    for key, payload_key in (("input_tokens", "inputTokens"), ("output_tokens", "outputTokens"), ("total_tokens", "totalTokens")):
        known = [e["payload"]["usage"][payload_key] for e in ends.values()
                 if isinstance(e["payload"].get("usage"), dict) and e["payload"]["usage"].get(payload_key) is not None]
        result[key] = sum(known) if complete else None
        result["known_partial_" + key] = sum(known) if known else None
    return result


def verify_supervisor_scope(events, has_attachments):
    failures = []
    allowed = set()
    completed = set()
    physical_completions = set()
    blocked = set()
    executed = set()
    scope_turns = model_turns = 0
    for event in events:
        family, name, actor = event["eventFamily"], event["eventName"], event.get("actorName")
        payload = event["payload"]
        if (family, name) == ("model", "completed"):
            physical_completions.add(payload.get("agentInvocationId"))
        elif (family, name) == ("agent", "completed") and actor in SPECIALIST_TOOLS.values():
            if payload.get("callId") in physical_completions:
                completed.add(actor)
        elif (family, name) == ("architecture", "tool_scope"):
            scope_turns += 1
            allowed = set(payload.get("allowedTools", []))
            mandatory_done = "attachments" in completed if has_attachments else bool(completed)
            expected = {"attachments_specialist"} if has_attachments and not mandatory_done else set(SPECIALIST_TOOLS)
            if (allowed != expected or payload.get("supervisorModelTurn") != scope_turns
                    or payload.get("mandatorySpecialistCompleted") is not mandatory_done
                    or payload.get("toolChoice") != ({"auto": {}} if mandatory_done else {"any": {}})):
                failures.append("invalid_supervisor_tool_scope")
        elif actor == "supervisor" and (family, name) == ("model", "started"):
            model_turns += 1
            if model_turns != scope_turns:
                failures.append("missing_supervisor_model_scope")
        elif actor == "supervisor" and family == "tool":
            call_id = payload.get("toolCallId")
            if name == "started":
                executed.add(call_id)
                if event.get("toolName") not in allowed:
                    failures.append("executed_tool_outside_supervisor_scope")
            elif name == "rejected":
                blocked.add(call_id)
                if event.get("toolName") in allowed:
                    failures.append("in_scope_tool_marked_rejected")
    if executed & blocked or scope_turns != model_turns:
        failures.append("inconsistent_supervisor_scope_trace")
    return failures


def verify_architectural_trace(architecture, events, reported=None, *, protocol=PROTOCOL_VERSION, has_attachments=False):
    """Verify recorded execution, never infer real agents from names or text alone."""
    failures = []
    contract = [e for e in events if e["eventFamily"] == "architecture" and e["eventName"] == "contract"]
    if len(contract) != 1:
        failures.append("missing_or_duplicate_contract_event")
    elif contract[0]["payload"].get("compliant") is not True:
        failures.extend(contract[0]["payload"].get("violations") or ["runtime_contract_failed"])
    if reported is False:
        failures.append("runtime_reported_contract_failed")
    agent_starts = [(i, e) for i, e in enumerate(events) if e["eventFamily"] == "agent" and e["eventName"] == "started"]
    specialist_starts = [(i, e) for i, e in agent_starts if e.get("actorName") in SPECIALIST_TOOLS.values()]
    if not specialist_starts:
        failures.append("no_specialist_agent_invocation")
    finals = [i for i, e in enumerate(events) if e["eventFamily"] == "response" and e["eventName"] == "final"]
    if protocol == V43 or (protocol == V44 and architecture == "centralized_orchestration"):
        specialist_ends = [(i, e) for i, e in enumerate(events) if e["eventFamily"] == "agent"
                           and e["eventName"] == "completed" and e.get("actorName") in SPECIALIST_TOOLS.values()]
        if len(finals) != 1 or not any(i < finals[0] for i, _ in specialist_ends):
            failures.append("no_completed_specialist_before_final")
        if has_attachments and (len(finals) != 1 or not any(
            i < finals[0] and e["actorName"] == "attachments" for i, e in specialist_ends
        )):
            failures.append("no_completed_attachment_specialist_before_final")
        if protocol == V43 and architecture == "decentralized_swarm" and (
            any(e.get("actorName") in {"coordinator", "synthesizer", "supervisor", "router"} for _, e in agent_starts)
            or any(events[i].get("actorName") not in SPECIALIST_TOOLS.values() for i in finals)
        ):
            failures.append("non_peer_agent_in_decentralized_condition")
    for i, start in specialist_starts:
        invocation = start["payload"].get("agentInvocationId", start["payload"].get("callId"))
        if not invocation or not any(e["eventFamily"] == "model" and e["eventName"] == "started"
                                    and e["payload"].get("agentInvocationId") == invocation for e in events[i + 1:]):
            failures.append("specialist_without_physical_model_request")
    if architecture == "centralized_orchestration":
        if protocol == V44:
            failures.extend(verify_supervisor_scope(events, has_attachments))
        tool_starts = [(i, e) for i, e in enumerate(events) if e["eventFamily"] == "tool" and e["eventName"] == "started" and e.get("toolName") in SPECIALIST_TOOLS]
        if not 1 <= len(tool_starts) <= 6:
            failures.append("specialist_tool_invocation_limit")
        if any(e["eventFamily"] == "tool" and e["eventName"] == "started" and
               ((e.get("actorName") == "supervisor" and e.get("toolName") in DOMAIN_TOOLS) or e.get("toolName") == "handoff_to_peer") for e in events):
            failures.append("forbidden_supervisor_domain_or_peer_tool")
        for i, tool_start in tool_starts:
            tid = tool_start["payload"]["toolCallId"]
            ends = [(j, e) for j, e in enumerate(events) if j > i and e["eventFamily"] == "tool" and e["eventName"] == "completed" and e["payload"].get("toolCallId") == tid]
            children = [(j, e) for j, e in specialist_starts if j > i and e["payload"].get("parentCallId") == tid and e.get("actorName") == SPECIALIST_TOOLS[tool_start["toolName"]]]
            if len(ends) != 1 or len(children) != 1:
                failures.append("specialist_tool_child_or_return_unverified")
                continue
            end_index, end = ends[0]
            child_index, child = children[0]
            invocation = child["payload"].get("agentInvocationId", child["payload"].get("callId"))
            completed = [j for j, e in enumerate(events) if child_index < j < end_index and e["eventFamily"] == "agent" and e["eventName"] == "completed" and e["payload"].get("callId") == invocation]
            if end.get("status") != "completed" or not completed or not finals or end_index >= finals[0]:
                failures.append("specialist_result_not_returned_before_final")
    return {"version": "architectural-trace-v1", "compliant": not failures,
            "violations": list(dict.fromkeys(failures))}


def worker(task_path):
    task = json.loads(task_path.read_text())
    case, unit = task["case"], task["unit"]
    settings = replace(get_settings(), enable_live_llm=True, **task["settings"])
    protocol = task.get("protocol", PROTOCOL_VERSION)
    request = make_request(case, unit, task["experiment_id"], protocol)
    out = Path(task["attempt_dir"])
    events = LocalEvents(out / "events.jsonl")
    started = time.monotonic()
    record = {**unit, "attempt_id": task["attempt_id"], "run_id": str(request.run_id),
              "started_at": datetime.now(UTC).isoformat(), "worker_pid": os.getpid(), "mode": "live",
              "reference_status": task.get('reference_status','provisional'), "transport": "direct-core-runtime"}
    dump(out / "started.json", record)
    try:
        result = RuntimeExecutor(request, settings=settings, callbacks=events).execute()
        record.update(asdict(result), status="completed" if result.final_text.strip() and result.final_outcome != "failed" else "failed", success=bool(result.final_text.strip()) and result.final_outcome != "failed")
    except Exception as exc:
        # Preserve traces privately; public summary uses error type only.
        import traceback
        (out / "error.txt").write_text(traceback.format_exc())
        record.update(status="limit_exceeded" if "ExperimentLimitExceeded" in str(type(exc)) else "error", success=False, error_type=type(exc).__name__)
    record.update(finished_at=datetime.now(UTC).isoformat(), latency_ms=(time.monotonic()-started)*1000)
    event_list = [json.loads(line) for line in events.path.read_text().splitlines()] if events.path.exists() else []
    if any(e["eventFamily"] == "limit" for e in event_list):
        record.update(status="limit_exceeded",success=False)
    elif any(e["eventFamily"] == "model" and e["eventName"] == "failed" for e in event_list):
        # Strands can turn a nested exception into a tool error and let the
        # supervisor finish. Preserve its text but retain the provider failure.
        record.update(status="failed_model_request", success=False)
    record.update(trace_measurements(event_list), inference_provenance="live-bedrock",
                  tool_provenance="deterministic-controlled-fixtures", comparison_protocol=protocol,
                  limit_exceeded=record["status"] == "limit_exceeded")
    if protocol in {PROTOCOL_VERSION, V43, V44}:
        contract = verify_architectural_trace(unit["architecture"], event_list, record.get("architectural_compliance"),
                                              protocol=protocol, has_attachments=bool(case.get("attachments")))
        record.update(architecture_contract=contract, architectural_compliance=contract["compliant"],
                      architectural_violations=contract["violations"])
    if protocol in {V43, V44}:
        if record.get("final_outcome") == "architectural_contract_failed":
            record["candidate_text"] = record.pop("final_text")
        record["provider_error_types"] = sorted({
            e["payload"].get("errorType", "unknown") for e in event_list
            if e["eventFamily"] == "model" and e["eventName"] == "failed"
        })
    dump(out / "result.json", record)


def build_order(cases, repetitions, seed, experiment_id, architecture_selection=ARCHITECTURES):
    rng = random.Random(seed)
    blocks = [(c, r) for c in cases for r in range(repetitions)]
    rng.shuffle(blocks)
    order = []
    permutations = list(itertools.permutations(architecture_selection))
    full, remainder = divmod(len(blocks),len(permutations))
    # Select the remainder that best balances positions, then randomize assignment.
    candidates = list(itertools.combinations(permutations,remainder))
    def imbalance(choice):
        counts=[sum(p[pos] == arch for p in choice) for arch in architecture_selection for pos in range(len(architecture_selection))]
        return max(counts,default=0)-min(counts,default=0)
    best=min(map(imbalance,candidates),default=0)
    extras=rng.choice([x for x in candidates if imbalance(x)==best]) if candidates else ()
    plans=permutations*full+list(extras); rng.shuffle(plans)
    for block_position, ((case, repetition), architectures) in enumerate(zip(blocks,plans)):
        for position, arch in enumerate(architectures):
            key = f'{case["id"]}:{repetition}:{arch}'
            order.append({"unit_id": str(uuid5(UUID(experiment_id), key)), "scenario_id": case["id"],
                          "stratum": case["stratum"], "difficulty": case["difficulty"],
                          "repetition": repetition, "architecture": arch, "block": block_position,
                          "block_id": f"block-{block_position:03d}", "position":position,
                          "block_position": position, "global_position": len(order), "randomization_seed": seed})
    return order


def stability_plan(order, seed=20261011):
    """Select planned units before responses exist, independent of their quality."""
    rng = random.Random(seed)
    units = []
    for arch in ARCHITECTURES:
        for stratum in ("faq", "stock", "attachments", "professional_review", "continuity"):
            choices = [u for u in order if u["architecture"] == arch and u["stratum"] == stratum]
            if choices:
                units.append(rng.choice(choices)["unit_id"])
    rng.shuffle(units)
    return {"version": "planned-unit-stability-v1", "seed": seed, "unit_ids": units,
            "selection": "one planned unit per architecture and stratum; no replacement for unavailable responses",
            "human_review_performed": False}


def default_analysis_plan():
    return {"version": "corrected-comparison-analysis-v1", "frozen_before_generation": True,
            "unit": "scenario; five repetitions remain grouped", "seed": 20261011,
            "success": "technical completion + architectural compliance + essentials + mandatory evidence + no critical violation",
            "missing": "retain all first attempts; unknown remains unknown; explicit denominators and bounds",
            "paired_success": {"effect": "mean of scenario success-rate differences in percentage points, B minus A",
                "bootstrap": "20000 paired percentile resamples of whole scenarios; 95% conditional interval",
                "test": "two-sided within-scenario label-swap sign permutation of scenario success-rate differences; 99999 samples with add-one correction",
                "multiplicity": "Holm across all three architecture pairs", "complete_pairs": "both architectures have five non-null task outcomes; excluded scenarios explicit"},
            "continuous": "scenario medians of five observed repetitions; scenario distributions and paired effects; no pooling repetitions as independent samples",
            "reliability": "distribution of 0 through 5 task successes, pass_1 and pass_5 with unknown bounds",
            "failure_precedence": ["technical", "architectural", "invalid_or_missing_judgment", "content_and_mandatory_source", "content_only", "mandatory_source_only", "unresolved"],
            "limitations": "intentional known sample; same judge recheck; no human or clinical validation; no causal historical claim"}


def validate_historical_dataset(path, cases):
    historical = json.loads(path.read_text())
    if cases != historical["cases"]:
        raise ValueError("Cases differ from historical frozen manifest; do not replace the original 40 scenarios")
    if len(cases) != 40:
        raise ValueError("Historical comparison requires exactly 40 scenarios")
    central_condition = "historical single agent with domain functions; not the corrected orchestrator"
    if historical.get("configuration", {}).get("protocol") == PROTOCOL_VERSION:
        central_condition = "v4.2 supervisor with specialist tools and prompt-only minimum delegation"
    return {"manifest_sha256": sha(path.read_bytes()), "experiment_id": historical["experiment_id"],
            "cases_sha256": historical["cases_sha256"], "dataset_version": historical["dataset_version"],
            "centralized_condition": central_condition}


def preserve_interrupted_attempt(attempt_dir, unit):
    """Recover a dead first attempt without ever launching that unit again."""
    launch = json.loads((attempt_dir / "launch.json").read_text()) if (attempt_dir / "launch.json").exists() else {}
    started_path = attempt_dir / "started.json"
    started = json.loads(started_path.read_text()) if started_path.exists() else {}
    pid = launch.get("pid") or started.get("worker_pid")
    if pid:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            pass
        else:
            raise RuntimeError("An earlier worker may still be alive; inspect it before resuming")
    task = json.loads((attempt_dir / "task.json").read_text())
    events_path = attempt_dir / "events.jsonl"
    events = [json.loads(x) for x in events_path.read_text().splitlines()] if events_path.exists() else []
    record = {**unit, "attempt_id": task["attempt_id"], "status": "interrupted", "success": False,
              "mode": "live", "comparison_protocol": task.get("protocol", PROTOCOL_VERSION), "transport": "direct-core-runtime",
              "finished_at": datetime.now(UTC).isoformat(), "interruption_recovered": True,
              "latency_ms": None, "end_to_end_latency_ms": None,
              "architectural_compliance": None, **trace_measurements(events)}
    dump(attempt_dir / "result.json", record)
    return record


def write_csv(path, rows, fields=None):
    if not rows and fields is None:
        return
    fields = fields or sorted(set().union(*(r.keys() for r in rows)))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def export(folder, records, cases):
    write_csv(folder / "runs.csv", records)
    # Deterministic derived exports; attempt journals remain append-only.
    def jsonl_export(name,rows):
        tmp=folder/(name+".tmp")
        tmp.write_text("".join(json.dumps(row,ensure_ascii=False)+"\n" for row in rows)); tmp.replace(folder/name)
    jsonl_export("runs.jsonl",records)
    all_events=[]
    for r in records:
        path=folder/r["unit_id"]/"events.jsonl"
        if path.exists():
            all_events.extend({"attempt_id":r["attempt_id"],**json.loads(line)} for line in path.read_text().splitlines())
    jsonl_export("events.jsonl",all_events)
    jsonl_export("calls.jsonl",[e for e in all_events if e["eventFamily"] in {"model","tool","handoff","communication"}])
    jsonl_export("responses.jsonl",[{"response_id":sha((r["attempt_id"]+"blind-v1").encode())[:24], "attempt_id":r["attempt_id"], "response":r.get("final_text"), "response_available":bool(r.get("final_text", "").strip()), "evidence_refs":[] } for r in records])
    blind = []
    forms = []
    by_case = {c["id"]: c for c in cases}
    for r in records:
        if not r.get("final_text", "").strip():
            continue
        evaluation_id = sha((r["attempt_id"] + "blind-v1").encode())[:24]
        blind.append({"evaluation_id": evaluation_id, "input": by_case[r["scenario_id"]], "response": r["final_text"]})
        for reviewer in ("pharmacist_1", "pharmacist_2"):
            forms.append({"evaluation_id": evaluation_id, "reviewer_id": reviewer,
                          **{d: "" for d in ("correctness", "completeness", "clarity", "context", "safety")},
                          "referral_adequacy": "", "critical_error": "", "justification": ""})
    random.Random(1031).shuffle(blind)
    dump(folder / "blind-responses.json", blind)
    dump(folder / "blind-mapping.json", {sha((r["attempt_id"]+"blind-v1").encode())[:24]: r["attempt_id"] for r in records if r.get("final_text", "").strip()})
    write_csv(folder / "pharmacist-scores-template.csv", forms,
              ["evaluation_id", "reviewer_id", "correctness", "completeness", "clarity", "context", "safety", "referral_adequacy", "critical_error", "justification"])
    manifest=json.loads((folder / 'manifest.json').read_text())
    summary = {"planned": len(manifest["order"]),
               "attempts": len(records), "completed": sum(bool(r.get("success")) for r in records),
               "failed": sum(not r.get("success") for r in records), "human_review_performed": False,
               "architecturally_compliant": sum(r.get("architectural_compliance") is True for r in records),
               "architectural_violations": sum(r.get("architectural_compliance") is False for r in records),
               "responses_available": sum(bool(r.get("final_text", "").strip()) for r in records),
               "dataset_version":manifest.get('dataset_version'),"cohort":manifest.get('cohort','pilot'),
               "scope": "direct core runtime; technical references without clinical validation; descriptive analysis only"}
    dump(folder / "summary.json", summary)
    return summary


def collect_parallel_unit(folder, manifest, case, unit, stop, wave, wave_size):
    """One process and one durable first-attempt directory for each planned unit."""
    attempt_dir = folder / unit["unit_id"]
    attempt_dir.mkdir(exist_ok=True)
    result_path = attempt_dir / "result.json"
    if result_path.exists():
        return json.loads(result_path.read_text())
    if (attempt_dir / "started.json").exists() or (attempt_dir / "launch.json").exists():
        record = preserve_interrupted_attempt(attempt_dir, unit)
        record.update(generation_wave=wave, generation_wave_size=wave_size,
                      collector_finished_at=datetime.now(UTC).isoformat())
        dump(result_path, record)
        return record
    if stop.is_set():
        return None

    attempt_id = str(uuid4())
    task_path = attempt_dir / "task.json"
    dump(task_path, {"case": case, "unit": unit, "experiment_id": manifest["experiment_id"],
                     "attempt_id": attempt_id, "reference_status": manifest["reference_status"],
                     "settings": manifest["settings"], "attempt_dir": str(attempt_dir),
                     "protocol": manifest["configuration"]["protocol"]})
    launch = {"attempt_id": attempt_id, "started_at": datetime.now(UTC).isoformat(),
              "wave": wave, "wave_size": wave_size, "pid": None}
    launch_path = attempt_dir / "launch.json"
    dump(launch_path, launch)
    launched_at = time.monotonic()
    deadline = launched_at + manifest["settings"]["runtime_timeout_seconds"]
    proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--worker", str(task_path)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    failure = "worker_failed"
    try:
        dump(launch_path, {**launch, "pid": proc.pid})
        while proc.poll() is None:
            if stop.is_set() or time.monotonic() >= deadline:
                failure = "cancelled" if stop.is_set() else "timeout"
                break
            stop.wait(0.1)
    finally:
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
    if result_path.exists():
        record = json.loads(result_path.read_text())
    else:
        record = preserve_interrupted_attempt(attempt_dir, unit)
        record["status"] = failure
    record.update(end_to_end_latency_ms=(time.monotonic() - launched_at) * 1000,
                  generation_wave=wave, generation_wave_size=wave_size,
                  collector_finished_at=datetime.now(UTC).isoformat())
    dump(result_path, record)
    return record


def collect_parallel(folder, manifest, continue_after_failure):
    workers = manifest["generation_dispatch"]["workers"]
    cases = {case["id"]: case for case in manifest["cases"]}
    order = manifest["order"]
    records = {}
    stop = Event()
    began = time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for offset in range(0, len(order), workers):
            if manifest["code_hashes"] != code_hashes():
                raise RuntimeError("Code changed during experiment; remaining executions stopped")
            validate_environment(manifest)
            wave = order[offset:offset + workers]
            previously_terminal = {unit["unit_id"] for unit in wave
                                   if (folder / unit["unit_id"] / "result.json").exists()}
            futures = [pool.submit(collect_parallel_unit, folder, manifest, cases[unit["scenario_id"]],
                                   unit, stop, offset // workers + 1, len(wave)) for unit in wave]
            wave_records = []
            try:
                for future in as_completed(futures):
                    record = future.result()
                    wave_records.append(record)
                    records[record["unit_id"]] = record
                    if record["unit_id"] not in previously_terminal:
                        append(folder / "attempts.jsonl", record)
            except BaseException:
                stop.set()
                raise
            dump(folder / "generation-progress.json", {
                "terminal": len(records), "planned": len(order), "workers": workers,
                "finished_wave": offset // workers + 1,
                "elapsed_seconds_this_dispatch": time.monotonic() - began,
                "updated_at": datetime.now(UTC).isoformat(),
            })
            failed = sum(not record["success"] for record in wave_records)
            print(f"Generation {len(records)}/{len(order)}; wave {offset // workers + 1}; technical failures {failed}",
                  flush=True)
            unavailable = {"ModelThrottledException", "ThrottlingException", "ServiceUnavailableException",
                           "ModelNotReadyException", "ExpiredTokenException", "AccessDeniedException"}
            new_records = [record for record in wave_records if record["unit_id"] not in previously_terminal]
            if any(unavailable.intersection(record.get("provider_error_types", [])) for record in new_records):
                print("Provider capacity or authorization error; paused after a complete wave", flush=True)
                break
            if any(not record["success"] for record in new_records) and not continue_after_failure:
                break
    ordered = [records[unit["unit_id"]] for unit in order if unit["unit_id"] in records]
    summary = export(folder, ordered, manifest["cases"])
    print(json.dumps(summary), flush=True)
    return 0 if not summary["failed"] and len(ordered) == len(order) else 1


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "experiments/pilots-v5/pilot-b.json")
    parser.add_argument("--output", type=Path, default=ROOT / "var/reports/research-pilot" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--calibration",type=Path,default=ROOT / "var/reports/automated-pilots-v5/calibration-v5.2")
    parser.add_argument("--seed", type=int, default=20261011)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--model")
    parser.add_argument("--region")
    parser.add_argument("--protocol", choices=(PROTOCOL_VERSION, V43, V44), default=PROTOCOL_VERSION)
    parser.add_argument("--generation-workers", type=int, default=1)
    parser.add_argument("--judge-workers", type=int, default=1,
                        help="Freeze the v4.4 evaluation dispatch without changing the instrument")
    parser.add_argument("--case", action="append")
    parser.add_argument("--architecture", action="append", choices=ARCHITECTURES,
                        help="Restrict a separate verification round; default compares all three")
    parser.add_argument("--historical-manifest", type=Path, help="Require exact equality to the original frozen 40 cases")
    parser.add_argument("--analysis-plan", type=Path, help="JSON analysis plan frozen before generation")
    parser.add_argument("--continue-after-failure", action="store_true", help="Preserve technical failures and continue the planned units; never retry")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        worker(args.worker); return 0
    if args.repetitions < 1 or args.timeout < 1 or args.max_tokens < 1:
        parser.error("repetitions, timeout and max-tokens must be positive")
    if not args.resume:
        parallel = args.generation_workers != 1
        if args.protocol == V43 and not parallel:
            parser.error("v4.3 requires parallel generation")
        if parallel and (args.protocol not in {V43, V44} or args.architecture
                         or not 3 <= args.generation_workers <= 48 or args.generation_workers % 3):
            parser.error("Parallel generation requires v4.3 or v4.4, all three architectures and a worker multiple of three")
        if not 1 <= args.judge_workers <= 48:
            parser.error("The frozen judge worker count must be between 1 and 48")
    folder = args.output.resolve(); folder.mkdir(parents=True, exist_ok=True); folder.chmod(0o700)
    manifest_path = folder / "manifest.json"
    if args.resume:
        manifest = json.loads(manifest_path.read_text())
        if manifest["code_hashes"] != code_hashes():
            raise RuntimeError("Code differs from frozen manifest; start a separate pilot")
        validate_environment(manifest)
    else:
        if manifest_path.exists():
            raise RuntimeError("Output already exists; use --resume or a new output")
        catalogue = json.loads(args.cases.read_text())
        cases = [c for c in catalogue["cases"] if not args.case or c["id"] in args.case]
        if not cases or len({c["id"] for c in cases}) != len(cases):
            raise ValueError("Empty or duplicate case catalogue")
        if args.case and set(args.case) - {c["id"] for c in cases}:
            raise ValueError("Unknown case selection")
        if catalogue.get("version") in {"pilots-v4","pilots-v5"}:
            from app.experiments.methodology import validate_catalogue
            validate_catalogue(catalogue)
        settings = replace(get_settings(), enable_live_llm=True, runtime_timeout_seconds=args.timeout,
                           llm_max_tokens=args.max_tokens, llm_temperature=0.0,
                           bedrock_model_id=args.model or get_settings().bedrock_model_id,
                           aws_region=args.region or get_settings().aws_region)
        experiment_id = str(uuid4())
        from judge_automated_pilots import config as judge_config
        from app.experiments.methodology import (VERSION, OBJECTIVE_CHECK_VERSION,
                                                NESTED_PROCEDURE_PROTOCOLS, NESTED_OBJECTIVE_CHECK_VERSION)
        frozen_judge=judge_config()
        analysis_plan = json.loads(args.analysis_plan.read_text()) if args.analysis_plan else default_analysis_plan()
        historical = validate_historical_dataset(args.historical_manifest, cases) if args.historical_manifest else None
        configuration = snapshot(settings)
        if args.protocol == V43:
            from app.architectures.comparison_v43 import snapshot_v43
            configuration = snapshot_v43(settings)
        elif args.protocol == V44:
            from app.architectures.comparison_v44 import snapshot_v44
            configuration = snapshot_v44(settings)
        manifest = {"experiment_id": experiment_id, "created_at": datetime.now(UTC).isoformat(),
                    "dataset_version":catalogue.get('dataset_version',catalogue.get('version')),
                    "cohort":catalogue.get('cohort','pilot'),
                    "reference_status": catalogue["reference_status"], "cases": cases, "randomization_version":"balanced-permutations-v1", "human_review_performed":False, "repetitions":args.repetitions,
                    "environment": {"system":platform.system(),"machine":platform.machine(),"platform":platform.platform()},
                    "cases_sha256": sha(json.dumps(cases, sort_keys=True).encode()),
                    "code_hashes": code_hashes(), "commit": subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
                    "sdk_version": importlib.metadata.version("strands-agents"), "configuration": configuration,
                    "evaluation_plan":{"model_id":frozen_judge['model_id'],"temperature":0,"max_tokens":4096,"version":VERSION,
                        "objective_check_version":NESTED_OBJECTIVE_CHECK_VERSION if args.protocol in NESTED_PROCEDURE_PROTOCOLS else OBJECTIVE_CHECK_VERSION,
                        "calibration_folder":str(args.calibration.resolve()),"configuration_sha256":sha(json.dumps(frozen_judge,sort_keys=True,ensure_ascii=False).encode())},
                    "dependency_versions": dependency_versions(),
                    "asset_hashes": {str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(set([args.cases.resolve(), *args.cases.resolve().parent.glob("*.md"), *args.cases.resolve().parent.glob("*.json")]))},
                    "settings": {k: getattr(settings,k) for k in ("bedrock_model_id","aws_region","runtime_timeout_seconds","llm_temperature","llm_max_tokens","runtime_max_handoffs")},
                    "analysis_plan": analysis_plan, "analysis_plan_sha256": sha(json.dumps(analysis_plan,sort_keys=True,ensure_ascii=False).encode()),
                    "historical_reference": historical,
                    "measurement_boundaries": {"latency_ms": "core RuntimeExecutor plus local event instrumentation; excludes Python import/HTTP/database/UI/evaluation", "end_to_end_latency_ms": "historical collector process launch through worker exit and result-file completion; includes imports/core/local instrumentation; excludes HTTP/database/UI/evaluation"},
                    "order": build_order(cases, args.repetitions, args.seed, experiment_id,
                                         tuple(dict.fromkeys(args.architecture)) if args.architecture else ARCHITECTURES)}
        manifest["stability_recheck_plan"] = stability_plan(manifest["order"], args.seed) if len(manifest["order"]) == 600 else {"version":"engineering-pilot-no-stability-recheck", "unit_ids":[], "seed":args.seed}
        if args.protocol == V43 or (args.protocol == V44 and args.generation_workers > 1):
            manifest["generation_dispatch"] = {
                "workers": args.generation_workers,
                "mode": "balanced concurrent waves of complete scenario-repetition triplets",
                "policy": "one isolated subprocess per first attempt; all triplets in a wave finish before the next wave",
            }
            manifest["measurement_boundaries"]["latency_ms"] += "; measured under mixed-architecture concurrent load"
            manifest["measurement_boundaries"]["end_to_end_latency_ms"] += "; excludes time awaiting wave admission"
            if args.protocol == V43 and catalogue.get("cohort") == V43_MAIN_COHORT:
                manifest["stability_recheck_plan"] = stability_plan(manifest["order"], args.seed)
        elif args.protocol == V44:
            manifest["generation_dispatch"] = {
                "workers": 1,
                "mode": "sequential",
                "policy": "one isolated subprocess per first attempt, in frozen balanced order",
            }
        if args.protocol == V44:
            manifest["evaluation_plan"]["dispatch_workers"] = args.judge_workers
        for name, expected in manifest["code_hashes"].items():
            source = ROOT / name
            if sha(source.read_bytes()) != expected:
                raise RuntimeError("Source changed while freezing experiment")
            dest = folder / "code-snapshot" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        for name in manifest["asset_hashes"]:
            dest=folder/"assets-snapshot"/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
        dump(manifest_path, manifest)
        dump(folder / "analysis-plan.json", analysis_plan)
        dump(folder / "stability-recheck-plan.json", manifest["stability_recheck_plan"])
        write_csv(folder / "execution-order.csv", manifest["order"])
    generation_workers = manifest.get("generation_dispatch", {}).get("workers", 1)
    print(f'Planned: {len(manifest["order"])} live executions; generation workers: {generation_workers}; output: {folder}',
          flush=True)
    if args.plan_only:
        return 0
    calibration=Path(manifest['evaluation_plan']['calibration_folder'])
    if not (calibration/'calibration-gate.json').exists() or not json.loads((calibration/'calibration-gate.json').read_text()).get('passed'):
        raise RuntimeError('Live agent collection requires the frozen technical calibration gate')
    cfg=json.loads((calibration/'judge-config.json').read_text())
    if sha(json.dumps(cfg,sort_keys=True,ensure_ascii=False).encode())!=manifest['evaluation_plan']['configuration_sha256']:
        raise RuntimeError('Calibration configuration differs from the frozen evaluation plan')
    protocol = manifest["configuration"]["protocol"]
    if protocol == V44 and len(manifest["order"]) == 600:
        gate = json.loads((folder / "engineering-gate.json").read_text())
        if not gate.get("passed") or gate.get("main_manifest_sha256") != sha(manifest_path.read_bytes()):
            raise RuntimeError("The technical pilot gate does not release this frozen main cohort")
    if generation_workers > 1:
        if protocol == V43 and manifest["cohort"] == V43_MAIN_COHORT:
            from human_review_v43 import checked_sample, load_manifest
            checked_sample(folder, *load_manifest(folder))
        # The kernel releases this lock if the dispatcher exits unexpectedly.
        # Durable per-unit launch and result markers still govern any resumption.
        with (folder / "generation.lock").open("a") as lock_stream:
            fcntl.flock(lock_stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return collect_parallel(folder, manifest, args.continue_after_failure)
    # Historical local lock rejects simultaneous runners.
    lock = folder / "runner.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.write(fd, str(os.getpid()).encode()); os.close(fd)
    records = []
    try:
        for unit in manifest["order"]:
            if manifest["code_hashes"] != code_hashes():
                raise RuntimeError("Code changed during experiment; remaining executions stopped")
            validate_environment(manifest)
            attempt_dir = folder / unit["unit_id"]; attempt_dir.mkdir(exist_ok=True)
            result_path = attempt_dir / "result.json"
            if result_path.exists():
                terminal=json.loads(result_path.read_text())
                records.append(terminal); continue
            if (attempt_dir / "started.json").exists() or (attempt_dir / "launch.json").exists():
                terminal = preserve_interrupted_attempt(attempt_dir, unit)
                records.append(terminal); append(folder / "attempts.jsonl", terminal)
                continue
            attempt_id = str(uuid4())
            task = {"case": next(c for c in manifest["cases"] if c["id"] == unit["scenario_id"]),
                    "unit": unit, "experiment_id": manifest["experiment_id"], "attempt_id": attempt_id,
                    "reference_status":manifest['reference_status'],
                    "settings": manifest["settings"], "attempt_dir": str(attempt_dir), "protocol": protocol}
            dump(attempt_dir / "task.json", task)
            launch_time = time.monotonic()
            proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--worker", str(attempt_dir / "task.json")],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            dump(attempt_dir / "launch.json", {"pid": proc.pid, "attempt_id": attempt_id, "started_at": datetime.now(UTC).isoformat()})
            try:
                proc.wait(timeout=manifest["settings"]["runtime_timeout_seconds"])
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                os.killpg(proc.pid, signal.SIGKILL); proc.wait()
                if not result_path.exists():
                    terminal = preserve_interrupted_attempt(attempt_dir, unit)
                    terminal.update(status="cancelled" if isinstance(sys.exc_info()[1], KeyboardInterrupt) else "timeout",
                                    end_to_end_latency_ms=(time.monotonic()-launch_time)*1000)
                    dump(result_path, terminal)
                if isinstance(sys.exc_info()[1], KeyboardInterrupt):
                    raise
            if not result_path.exists():
                terminal = preserve_interrupted_attempt(attempt_dir, unit)
                terminal.update(status="worker_failed", end_to_end_latency_ms=(time.monotonic()-launch_time)*1000)
                dump(result_path, terminal)
            record = json.loads(result_path.read_text()); record["end_to_end_latency_ms"]=(time.monotonic()-launch_time)*1000
            dump(result_path,record); records.append(record)
            append(folder / "attempts.jsonl", record)
            print(f'{unit["global_position"]+1}/{len(manifest["order"])} {unit["scenario_id"]} {unit["architecture"]}: {record["status"]}',flush=True)
            if protocol != V44:
                export(folder, records, manifest["cases"])
            elif set(record.get("provider_error_types", [])) & {
                "ExpiredTokenException", "AccessDeniedException", "UnrecognizedClientException",
                "ModelThrottledException", "ThrottlingException", "ServiceUnavailableException",
            }:
                print("Provider unavailable; first attempt preserved. Resume once access is restored.", flush=True)
                return 1
            if not record.get("success") and not args.continue_after_failure:
                print("Stopped at failed attempt; original is preserved, no automatic replacement.", flush=True)
                return 1
        summary = export(folder, records, manifest["cases"])
        print(json.dumps(summary),flush=True)
        return 0 if summary["failed"] == 0 else 1
    finally:
        lock.unlink(missing_ok=True)
        export(folder, records, manifest["cases"])


if __name__ == "__main__":
    raise SystemExit(main())
