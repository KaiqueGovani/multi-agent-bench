#!/usr/bin/env python3
"""Reproducible judge-only dispatcher. Frozen generation and judge semantics are unchanged.

Four independent processes own disjoint blind response IDs. Each logical response
has a durable claim and its own original judge_once journal. Only the coordinator
consolidates those physical request records into the cohort's canonical files.
No model call occurs without --allow-inference (or through any test command).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import judge_automated_pilots as judge
import run_research_pilot as collector

VERSION = "exclusive-parallel-judge-v1"
TERMINALS = {"completed", "failed"}


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text())


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def config_hash(cfg):
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def phase_path(folder, phase):
    return folder / "parallel-judging" / phase


def evaluation_name(phase):
    return "evaluations.jsonl" if phase == "primary" else "reevaluations.jsonl"


def validate_config(folder, calibration):
    cfg = judge.config()
    manifest = read(folder / "manifest.json")
    if not read(calibration / "calibration-gate.json").get("passed"):
        raise ValueError("Frozen technical calibration gate is not approved")
    if read(calibration / "judge-config.json") != cfg:
        raise ValueError("Judge differs from frozen calibrated configuration")
    if config_hash(cfg) != manifest["evaluation_plan"]["configuration_sha256"]:
        raise ValueError("Judge differs from cohort's frozen evaluation plan")
    if cfg["prompt_sha256"] != "ac77d9d9800bd6830102e5760a4d848330c3bcfcfa6d65b7d5723713f9478e36":
        raise ValueError("Historical semantic system prompt changed")
    if collector.code_hashes() != manifest["code_hashes"]:
        raise ValueError("Frozen generation/evaluation sources changed")
    judge.frozen_config(folder, cfg)
    return cfg


def canonical_dispositions(folder, phase):
    valid = {row["response_id"]: row for row in lines(folder / evaluation_name(phase))}
    failed = {row["response_id"]: row for row in lines(folder / "evaluation-failures.jsonl") if row["phase"] == phase}
    if set(valid) & set(failed):
        raise ValueError("Both valid and failed canonical dispositions for one response")
    return valid, failed


def make_result(value, aid, rid, phase, *, reason=None):
    if value is not None:
        return {"kind": "valid", "row": {"response_id": rid, "attempt_id": aid,
                "configuration_version": judge.VERSION, "evaluation": value,
                "human_review_performed": False}}
    return {"kind": "failure", "row": {"response_id": rid, "attempt_id": aid,
            "phase": phase, "reason": reason or "original_judge_schema_or_inference_failure"}}


def recover_from_journal(unit, case, rid, phase):
    """Never request another judgment after a durable physical start."""
    journal = lines(unit / "judge-attempts.jsonl")
    valid = [event for event in journal if event["event"] == "completed" and event.get("valid") is True]
    if valid:
        saved = valid[0]  # first durable valid format, never the favorable content
        decoded, _ = judge.normalize_json_format(saved["raw_output"])
        value = judge.validate_evaluation(decoded, case, rid)
        result = make_result(value, saved["attempt_id"], rid, phase)
        result["recovered_without_inference"] = True
    else:
        aid = next((event["attempt_id"] for event in reversed(journal) if event.get("attempt_id")), None)
        result = make_result(None, aid, rid, phase, reason="interrupted_owner_preserved_no_replacement")
    collector.dump(unit / "result.json", result)
    return result


def prepare(folder, calibration, workers, phase, *, expected_units=600):
    cfg = validate_config(folder, calibration)
    manifest = read(folder / "manifest.json")
    if (folder / "runner.lock").exists():
        raise ValueError("Generation is still running; do not overlap judge dispatch")
    if len(lines(folder / "runs.jsonl")) != len(manifest["order"]) or len(manifest["order"]) != expected_units:
        raise ValueError("Complete generation is required before judge dispatch")
    blind = read(folder / "blind-responses.json")
    ids = [row["evaluation_id"] for row in blind]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r"[a-f0-9]{24}", rid) for rid in ids):
        raise ValueError("Invalid or duplicate blind response identities")
    if phase == "recheck":
        selection = folder / "recheck-selection.json"
        if not selection.exists():
            selected = judge.select_rechecks(manifest, blind, read(folder / "blind-mapping.json"), lines(folder / "runs.jsonl"))
            collector.dump(selection, {"seed": 20261011, "response_ids": selected,
                "planned_unit_ids": manifest.get("stability_recheck_plan", {}).get("unit_ids"),
                "unavailable_responses": len(manifest.get("stability_recheck_plan", {}).get("unit_ids", selected)) - len(selected),
                "replacement_permitted": False})
        selected = set(read(selection)["response_ids"])
        blind = [row for row in blind if row["evaluation_id"] in selected]
        if len(blind) != len(selected):
            raise ValueError("Recheck selection includes unavailable blind responses")
    base = phase_path(folder, phase)
    dispatch_path = base / "dispatch.json"
    if dispatch_path.exists():
        dispatch = read(dispatch_path)
        if dispatch["workers"] != workers or dispatch["source_sha256"] != sha(Path(__file__)) or dispatch["configuration_sha256"] != config_hash(cfg):
            raise ValueError("Immutable dispatch/source/config differs; do not repartition")
        if dispatch["manifest_sha256"] != sha(folder / "manifest.json") or dispatch["blind_responses_sha256"] != sha(folder / "blind-responses.json"):
            raise ValueError("Frozen cohort manifest or blind responses changed")
        for worker, digest in dispatch["partition_sha256"].items():
            if sha(base / f"worker-{int(worker):02d}" / "blind-partition.json") != digest:
                raise ValueError("Immutable blind ownership partition changed")
        return dispatch
    valid, failed = canonical_dispositions(folder, phase)
    existing = set(valid) | set(failed)
    journal = [event for event in lines(folder / "judge-attempts.jsonl") if event.get("phase") == phase]
    started = {event["response_id"] for event in journal if event["event"] == "started"}
    unfinished = started - existing
    if unfinished:
        raise ValueError("Existing central starts lack dispositions; inspect/finish them before exclusive parallel transition")
    eligible = [row for row in blind if row["evaluation_id"] not in existing and row["evaluation_id"] not in started]
    base.mkdir(parents=True, mode=0o700)
    assignments = [{"response_id": row["evaluation_id"], "worker": index % workers + 1,
                    "position": index} for index, row in enumerate(eligible)]
    dispatch = {"version": VERSION, "created_at": now(), "phase": phase, "workers": workers,
                "source_sha256": sha(Path(__file__)), "configuration_sha256": config_hash(cfg),
                "semantic_system_prompt_sha256": cfg["prompt_sha256"],
                "manifest_sha256": sha(folder / "manifest.json"), "original_terminal_responses": len(existing),
                "blind_responses_sha256": sha(folder / "blind-responses.json"),
                "planned_blind_responses": len(blind), "new_owned_responses": len(eligible),
                "partition": "remaining blind order, fixed round-robin; one owner per response",
                "assignments": assignments, "generator_order_changed": False,
                "model_rubric_reference_changed": False, "new_model_calls_during_preparation": 0,
                "journal_merge": "original prefix then newly owned responses in immutable blind order; actual started_at preserves request concurrency; per-response journals are duplicate audit views, not extra physical requests",
                "resume": "completed owner retained; dead started owner recovers first valid durable output or becomes unknown, never another inference; only unclaimed logical units can start",
                "change_authorization": "user explicitly requested judge-only parallelism; generation remains sequential"}
    original = base / "original-prefix"
    original.mkdir(mode=0o700)
    for filename in ("judge-attempts.jsonl", "evaluations.jsonl", "reevaluations.jsonl", "evaluation-failures.jsonl"):
        source = folder / filename
        (original / filename).write_bytes(source.read_bytes() if source.exists() else b"")
    collector.dump(base / "judge-config.json", cfg)
    shutil.copyfile(Path(__file__), base / "adapter-source.py")
    for worker in range(1, workers + 1):
        path = base / f"worker-{worker:02d}"
        path.mkdir(mode=0o700)
        partition = [row for index, row in enumerate(eligible) if index % workers + 1 == worker]
        collector.dump(path / "blind-partition.json", partition)
    dispatch["partition_sha256"] = {str(worker): sha(base / f"worker-{worker:02d}" / "blind-partition.json")
                                    for worker in range(1, workers + 1)}
    collector.dump(dispatch_path, dispatch)  # immutable ownership persisted before inference
    collector.dump(base / "DISPATCH_AMENDMENT.json", {key: value for key, value in dispatch.items() if key != "assignments"})
    return dispatch


def execute_one(folder, dispatch, item, worker, cfg, *, engine=None):
    engine = engine or judge.judge_once
    rid = item["evaluation_id"]
    assignment = next((row for row in dispatch["assignments"] if row["response_id"] == rid), None)
    if not assignment or assignment["worker"] != worker:
        raise ValueError("Worker does not own this blind response")
    phase = dispatch["phase"]
    unit = phase_path(folder, phase) / "responses" / rid
    unit.mkdir(parents=True, exist_ok=True, mode=0o700)
    result_path, claim = unit / "result.json", unit / "claim.json"
    if result_path.exists():
        return read(result_path)
    if claim.exists():
        owner = read(claim)
        if owner["worker"] != worker:
            raise ValueError("Durable claim belongs to another owner")
        if alive(owner.get("pid")):
            raise RuntimeError("Claim owner may still be running; do not replace")
        return recover_from_journal(unit, item["input"], rid, phase)
    fd = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump({"response_id": rid, "worker": worker, "pid": os.getpid(),
                   "phase": phase, "claimed_at": now(), "configuration_sha256": config_hash(cfg)}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        value, aid = engine(unit, cfg, item["input"], item["response"], rid, phase)
        result = make_result(value, aid, rid, phase)
    except Exception as exc:
        # Preserve any request already started. No retry or favorable selection.
        result = recover_from_journal(unit, item["input"], rid, phase)
        result["owner_error_type"] = type(exc).__name__
    collector.dump(result_path, result)
    return result


def worker_main(folder, phase, index):
    base = phase_path(folder, phase)
    dispatch = read(base / "dispatch.json")
    if dispatch["source_sha256"] != sha(Path(__file__)):
        raise ValueError("Private dispatcher changed after ownership freeze")
    cfg = read(base / "judge-config.json")
    if cfg != judge.config() or config_hash(cfg) != dispatch["configuration_sha256"]:
        raise ValueError("Worker judge configuration is not the frozen configuration")
    if dispatch["manifest_sha256"] != sha(folder / "manifest.json") or dispatch["blind_responses_sha256"] != sha(folder / "blind-responses.json"):
        raise ValueError("Worker sees changed cohort inputs")
    if sha(base / f"worker-{index:02d}" / "blind-partition.json") != dispatch["partition_sha256"][str(index)]:
        raise ValueError("Worker ownership partition changed")
    items = read(base / f"worker-{index:02d}" / "blind-partition.json")
    for position, item in enumerate(items):
        execute_one(folder, dispatch, item, index, cfg)
        collector.dump(base / f"worker-{index:02d}" / "status.json",
                       {"worker": index, "phase": phase, "finished_or_preserved": position + 1,
                        "assigned": len(items), "updated_at": now()})
    return 0


class CentralMerge:
    def __init__(self, folder, dispatch):
        self.folder, self.dispatch = folder, dispatch
        self.base = phase_path(folder, dispatch["phase"])
        self.files = ("judge-attempts.jsonl", "evaluations.jsonl", "reevaluations.jsonl", "evaluation-failures.jsonl")
        self.sizes = {name: (folder / name).stat().st_size if (folder / name).exists() else 0 for name in self.files}
        for name in self.files:
            prefix = (self.base / "original-prefix" / name).read_bytes()
            actual = (folder / name).read_bytes() if (folder / name).exists() else b""
            if not actual.startswith(prefix):
                raise ValueError("Original sequential prefix was changed")
        self.events = {}
        for event in lines(folder / "judge-attempts.jsonl"):
            key = (event["attempt_id"], event["event"])
            if key in self.events:
                raise ValueError("Canonical physical judge event is duplicated")
            self.events[key] = event
        self.valid = {phase: {row["response_id"]: row for row in lines(folder / evaluation_name(phase))}
                      for phase in ("primary", "recheck")}
        self.failed = {(row["phase"], row["response_id"]): row for row in lines(folder / "evaluation-failures.jsonl")}

    def append(self, name, value):
        current = (self.folder / name).stat().st_size if (self.folder / name).exists() else 0
        if current != self.sizes[name]:
            raise ValueError("Another writer changed canonical judgment files during dispatch")
        collector.append(self.folder / name, value)
        self.sizes[name] = (self.folder / name).stat().st_size

    def merge_ready(self):
        phase = self.dispatch["phase"]
        merged = 0
        for assignment in self.dispatch["assignments"]:
            rid = assignment["response_id"]
            unit = self.base / "responses" / rid
            if not (unit / "result.json").exists():
                break  # deterministic blind order, actual timing remains in journal
            for event in lines(unit / "judge-attempts.jsonl"):
                if event["response_id"] != rid or event["phase"] != phase:
                    raise ValueError("Owner journal contains another blind response/phase")
                key = (event["attempt_id"], event["event"])
                if key in self.events:
                    if self.events[key] != event:
                        raise ValueError("Same physical event ID has different data")
                else:
                    self.append("judge-attempts.jsonl", event)
                    self.events[key] = event
            source = unit / "judge-inputs" / phase / (rid + ".json")
            destination = self.folder / "judge-inputs" / phase / (rid + ".json")
            if source.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists() and source.read_bytes() != destination.read_bytes():
                    raise ValueError("Canonical blinded judge input changed")
                if not destination.exists():
                    shutil.copyfile(source, destination)
            result = read(unit / "result.json")
            row = result["row"]
            if row["response_id"] != rid:
                raise ValueError("Wrong logical result owner")
            if result["kind"] == "valid":
                if (phase, rid) in self.failed:
                    raise ValueError("Cannot replace a preserved failed first judgment")
                if rid in self.valid[phase]:
                    if self.valid[phase][rid] != row:
                        raise ValueError("Cannot replace original primary/recheck evaluation")
                else:
                    self.append(evaluation_name(phase), row)
                    self.valid[phase][rid] = row
            else:
                if rid in self.valid[phase]:
                    raise ValueError("Cannot invalidate a preserved original judgment")
                if (phase, rid) in self.failed:
                    if self.failed[(phase, rid)] != row:
                        raise ValueError("Conflicting failure disposition")
                else:
                    self.append("evaluation-failures.jsonl", row)
                    self.failed[(phase, rid)] = row
            merged += 1
        return merged


def run_phase(folder, calibration, workers, phase, *, prepare_only=False):
    dispatch = prepare(folder, calibration, workers, phase)
    if prepare_only:
        print(json.dumps({"phase": phase, "prepared": dispatch["new_owned_responses"], "model_calls": 0}))
        return 0
    base = phase_path(folder, phase)
    merge = CentralMerge(folder, dispatch)
    processes, logs = [], []
    try:
        for index in range(1, workers + 1):
            log = (base / f"worker-{index:02d}" / "worker.log").open("a")
            logs.append(log)
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), str(folder),
                                        "--worker-index", str(index), "--phase", phase,
                                        "--allow-inference"], cwd=ROOT, stdout=log, stderr=log)
            processes.append(process)
        while any(process.poll() is None for process in processes):
            completed = merge.merge_ready()
            collector.dump(base / "status.json", {"phase": phase, "owned": dispatch["new_owned_responses"],
                           "merged": completed, "workers_running": sum(process.poll() is None for process in processes),
                           "updated_at": now()})
            time.sleep(0.5)
        # Dead owners with durable starts become preserved unknowns. Unclaimed
        # assignments remain unstarted and may be resumed, never substituted.
        by_rid = {item["evaluation_id"]: item for index in range(1, workers + 1)
                  for item in read(base / f"worker-{index:02d}" / "blind-partition.json")}
        for assignment in dispatch["assignments"]:
            unit = base / "responses" / assignment["response_id"]
            if (unit / "claim.json").exists() and not (unit / "result.json").exists():
                owner = read(unit / "claim.json")
                if alive(owner.get("pid")):
                    raise RuntimeError("An owner is still alive; cannot recover it")
                item = by_rid[assignment["response_id"]]
                recover_from_journal(unit, item["input"], item["evaluation_id"], phase)
        merged = merge.merge_ready()
        valid, failed = canonical_dispositions(folder, phase)
        summary = {"phase": phase, "workers": workers, "owned": dispatch["new_owned_responses"],
                   "merged": merged, "schema_valid_total": len(valid), "invalid_or_failed_total": len(failed),
                   "unstarted_remaining": dispatch["new_owned_responses"] - merged,
                   "worker_exit_codes": [process.returncode for process in processes], "completed_at": now()}
        collector.dump(base / "summary.json", summary)
        print(json.dumps(summary), flush=True)
        return 0 if merged == dispatch["new_owned_responses"] else 1
    finally:
        # Never kill a pending model request merely to transition dispatch.
        for process in processes:
            if process.poll() is None:
                process.wait()
        for log in logs:
            log.close()


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--phase", choices=("primary", "recheck", "both"), default="both")
    parser.add_argument("--workers", type=int, choices=(4,), default=4)
    parser.add_argument("--calibration", type=Path, default=ROOT / "var/reports/automated-pilots-v5/calibration-v5.2")
    parser.add_argument("--allow-inference", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--worker-index", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.allow_inference and not args.prepare_only:
        parser.error("Explicit --allow-inference or --prepare-only is required")
    folder = args.folder.resolve()
    if args.worker_index:
        if args.phase == "both" or args.worker_index not in range(1, 5):
            parser.error("Invalid private worker assignment")
        return worker_main(folder, args.phase, args.worker_index)
    lock = folder / "parallel-judge.lock"
    if lock.exists():
        if alive(read(lock).get("pid")) or not args.resume:
            raise RuntimeError("Judge dispatcher lock exists; inspect owner before --resume")
        shutil.copyfile(lock, folder / ("parallel-judge-stale-" + str(time.time_ns()) + ".json"))
        lock.unlink()
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump({"pid": os.getpid(), "created_at": now()}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        for phase in (("primary", "recheck") if args.phase == "both" else (args.phase,)):
            code = run_phase(folder, args.calibration.resolve(), args.workers, phase, prepare_only=args.prepare_only)
            if code:
                return code
        return 0
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
