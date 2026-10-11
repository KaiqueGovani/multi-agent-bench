#!/usr/bin/env python3
"""Sequential core-runtime pilot, immutable order, durable attempts and blind judging."""
from __future__ import annotations

import argparse
import csv
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
    files = list((ROOT / "apps/agent-runtime/app").rglob("*.py")) + list((ROOT / "scripts").glob("*research_pilot.py")) + list((ROOT / "scripts").glob("*automated_pilots.py"))
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


def make_request(case, unit, experiment_id):
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
            scenario_id=case["id"], comparisonProtocol=PROTOCOL_VERSION),
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


def worker(task_path):
    task = json.loads(task_path.read_text())
    case, unit = task["case"], task["unit"]
    settings = replace(get_settings(), enable_live_llm=True, **task["settings"])
    request = make_request(case, unit, task["experiment_id"])
    out = Path(task["attempt_dir"])
    events = LocalEvents(out / "events.jsonl")
    started = time.monotonic()
    record = {**unit, "attempt_id": task["attempt_id"], "run_id": str(request.run_id),
              "started_at": datetime.now(UTC).isoformat(), "mode": "live",
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
    calls = [e for e in event_list if e["eventFamily"] == "model"]
    agent_events = [e for e in event_list if e["eventFamily"] == "agent"]
    tools = [e for e in event_list if e["eventFamily"] == "tool" and e["eventName"] == "started"]
    starts = {e["payload"]["callId"] for e in calls if e["eventName"] == "started"}
    terminals = {e["payload"]["callId"]:e for e in calls if e["eventName"] in {"completed","failed"}}
    complete = bool(starts) and starts == set(terminals) and all(
        e["eventName"] == "completed" and isinstance(e["payload"].get("usage"),dict)
        and all(e["payload"]["usage"].get(k) is not None for k in ("inputTokens","outputTokens","totalTokens"))
        for e in terminals.values())
    record.update(agent_invocations=sum(e["eventName"] == "started" for e in agent_events),
        actual_agents=len({e["actorName"] for e in calls if e["eventName"] == "started"}),
        model_requests=len(starts), domain_tool_calls=sum(e["toolName"] in {"faq_lookup","stock_lookup","attachment_intake"} for e in tools),
        coordination_tool_calls=sum(e["toolName"] not in {"faq_lookup","stock_lookup","attachment_intake"} for e in tools),
        token_measurement_complete=complete, inference_provenance="live-bedrock", tool_provenance="deterministic-controlled-fixtures",
        limit_exceeded=record["status"] == "limit_exceeded")
    for key,payload_key in (("input_tokens","inputTokens"),("output_tokens","outputTokens"),("total_tokens","totalTokens")):
        known=[e["payload"]["usage"][payload_key] for e in terminals.values() if isinstance(e["payload"].get("usage"),dict) and e["payload"]["usage"].get(payload_key) is not None]
        record[key]=sum(known) if complete else None
        record["known_partial_"+key]=sum(known) if known else None
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
    jsonl_export("responses.jsonl",[{"response_id":sha((r["attempt_id"]+"blind-v1").encode())[:24], "attempt_id":r["attempt_id"], "response":r["final_text"], "evidence_refs":[] } for r in records if r.get("success")])
    blind = []
    forms = []
    by_case = {c["id"]: c for c in cases}
    for r in records:
        if not r.get("success"):
            continue
        evaluation_id = sha((r["attempt_id"] + "blind-v1").encode())[:24]
        blind.append({"evaluation_id": evaluation_id, "input": by_case[r["scenario_id"]], "response": r["final_text"]})
        for reviewer in ("pharmacist_1", "pharmacist_2"):
            forms.append({"evaluation_id": evaluation_id, "reviewer_id": reviewer,
                          **{d: "" for d in ("correctness", "completeness", "clarity", "context", "safety")},
                          "referral_adequacy": "", "critical_error": "", "justification": ""})
    random.Random(1031).shuffle(blind)
    dump(folder / "blind-responses.json", blind)
    dump(folder / "blind-mapping.json", {sha((r["attempt_id"]+"blind-v1").encode())[:24]: r["attempt_id"] for r in records if r.get("success")})
    write_csv(folder / "pharmacist-scores-template.csv", forms,
              ["evaluation_id", "reviewer_id", "correctness", "completeness", "clarity", "context", "safety", "referral_adequacy", "critical_error", "justification"])
    manifest=json.loads((folder / 'manifest.json').read_text())
    summary = {"planned": len(manifest["order"]),
               "attempts": len(records), "completed": sum(bool(r.get("success")) for r in records),
               "failed": sum(not r.get("success") for r in records), "human_review_performed": False,
               "dataset_version":manifest.get('dataset_version'),"cohort":manifest.get('cohort','pilot'),
               "scope": "direct core runtime; technical references without clinical validation; descriptive analysis only"}
    dump(folder / "summary.json", summary)
    return summary


def main():
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
    parser.add_argument("--case", action="append")
    parser.add_argument("--architecture", action="append", choices=ARCHITECTURES,
                        help="Restrict a separate verification round; default compares all three")
    parser.add_argument("--continue-after-failure", action="store_true", help="Preserve technical failures and continue the planned units; never retry")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        worker(args.worker); return 0
    if args.repetitions < 1 or args.timeout < 1 or args.max_tokens < 1:
        parser.error("repetitions, timeout and max-tokens must be positive")
    folder = args.output.resolve(); folder.mkdir(parents=True, exist_ok=True)
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
        from app.experiments.methodology import VERSION,OBJECTIVE_CHECK_VERSION
        frozen_judge=judge_config()
        manifest = {"experiment_id": experiment_id, "created_at": datetime.now(UTC).isoformat(),
                    "dataset_version":catalogue.get('dataset_version',catalogue.get('version')),
                    "cohort":catalogue.get('cohort','pilot'),
                    "reference_status": catalogue["reference_status"], "cases": cases, "randomization_version":"balanced-permutations-v1", "human_review_performed":False, "repetitions":args.repetitions,
                    "environment": {"system":platform.system(),"machine":platform.machine(),"platform":platform.platform()},
                    "cases_sha256": sha(json.dumps(cases, sort_keys=True).encode()),
                    "code_hashes": code_hashes(), "commit": subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
                    "sdk_version": importlib.metadata.version("strands-agents"), "configuration": snapshot(settings),
                    "evaluation_plan":{"model_id":frozen_judge['model_id'],"temperature":0,"max_tokens":4096,"version":VERSION,
                        "objective_check_version":OBJECTIVE_CHECK_VERSION,
                        "calibration_folder":str(args.calibration.resolve()),"configuration_sha256":sha(json.dumps(frozen_judge,sort_keys=True,ensure_ascii=False).encode())},
                    "dependency_versions": dependency_versions(),
                    "asset_hashes": {str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(set([args.cases.resolve(), *args.cases.resolve().parent.glob("*.md"), *args.cases.resolve().parent.glob("*.json")]))},
                    "settings": {k: getattr(settings,k) for k in ("bedrock_model_id","aws_region","runtime_timeout_seconds","llm_temperature","llm_max_tokens","runtime_max_handoffs")},
                    "order": build_order(cases, args.repetitions, args.seed, experiment_id,
                                         tuple(dict.fromkeys(args.architecture)) if args.architecture else ARCHITECTURES)}
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
        write_csv(folder / "execution-order.csv", manifest["order"])
    print(f'Planned: {len(manifest["order"])} sequential live executions; output: {folder}', flush=True)
    if args.plan_only:
        return 0
    calibration=Path(manifest['evaluation_plan']['calibration_folder'])
    if not (calibration/'calibration-gate.json').exists() or not json.loads((calibration/'calibration-gate.json').read_text()).get('passed'):
        raise RuntimeError('Live agent collection requires the frozen technical calibration gate')
    cfg=json.loads((calibration/'judge-config.json').read_text())
    if sha(json.dumps(cfg,sort_keys=True,ensure_ascii=False).encode())!=manifest['evaluation_plan']['configuration_sha256']:
        raise RuntimeError('Calibration configuration differs from the frozen evaluation plan')
    # Local lock rejects simultaneous runners. Stale lock requires explicit inspection.
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
                if terminal["status"] in {"timeout","cancelled","worker_failed"}:
                    raise RuntimeError("Interrupted worker requires explicit trace/process resolution before continuing; no automatic replacement")
                records.append(json.loads(result_path.read_text())); continue
            if (attempt_dir / "started.json").exists() or (attempt_dir / "launch.json").exists():
                raise RuntimeError("Unfinished attempt detected; inspect process/events before authorizing replacement")
            attempt_id = str(uuid4())
            task = {"case": next(c for c in manifest["cases"] if c["id"] == unit["scenario_id"]),
                    "unit": unit, "experiment_id": manifest["experiment_id"], "attempt_id": attempt_id,
                    "reference_status":manifest['reference_status'],
                    "settings": manifest["settings"], "attempt_dir": str(attempt_dir)}
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
                    dump(result_path, {**unit, "attempt_id": attempt_id, "status": "cancelled" if isinstance(sys.exc_info()[1], KeyboardInterrupt) else "timeout", "success": False,
                                       "latency_ms": (time.monotonic()-launch_time)*1000, "mode":"live"})
                if isinstance(sys.exc_info()[1], KeyboardInterrupt):
                    raise
            if not result_path.exists():
                dump(result_path, {**unit, "attempt_id": attempt_id, "status":"worker_failed", "success":False,
                                   "latency_ms": (time.monotonic()-launch_time)*1000, "mode":"live"})
            record = json.loads(result_path.read_text()); record["end_to_end_latency_ms"]=(time.monotonic()-launch_time)*1000
            dump(result_path,record); records.append(record)
            append(folder / "attempts.jsonl", record)
            print(f'{unit["global_position"]+1}/{len(manifest["order"])} {unit["scenario_id"]} {unit["architecture"]}: {record["status"]}',flush=True)
            export(folder, records, manifest["cases"])
            if record["status"] in {"timeout","cancelled","worker_failed"} or (not record.get("success") and not args.continue_after_failure):
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
