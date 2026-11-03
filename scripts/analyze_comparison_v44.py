#!/usr/bin/env python3
"""Export a complete v4.4 cohort from canonical private ledgers."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timedelta, timezone
from itertools import combinations, product
import json
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np

from analyze_comparison_v43 import DEFAULT_PRICING, measurement_summary, tri_state
from human_review_v43 import canonical_digest, digest, index_records, new_directory, read_json, read_jsonl, write_json_new
from summarize_corrected_comparison import (
    ARCHES, DIMS, ROOT, content_status, csvwrite, failure_class, figures, holm, inconsistent_judgment,
    ledger_summary, med, paired_success, summary, table,
)


PROTOCOL = "architectural-comparison-v4.4"
HISTORICAL_MANIFEST = ROOT / "research-data/private/agents-as-tools-v42/main-600-01/manifest.json"
PHASES = ("generation", "primary", "recheck")
PARALLEL_DISPATCH = "balanced concurrent waves of complete scenario-repetition triplets"
MAX_JUDGE_WORKERS = 48
MEASUREMENTS = ("latency_ms", "end_to_end_latency_ms", "total_tokens", "estimated_generation_cost_usd")
COUNT_FIELDS = ("input_tokens", "output_tokens", "total_tokens", "actual_agents", "agent_invocations", "model_requests",
                "domain_tool_calls", "coordination_tool_calls", "specialist_tool_invocations", "handoffs_requested",
                "handoffs_completed", "handoffs_failed", "inter_agent_messages", "inter_agent_characters", "domain_errors",
                "coordination_errors", "inter_agent_explicit_messages", "workflow_stage_count", "swarm_sdk_cycles",
                "generation_wave", "generation_wave_size", "scope_rejected_tool_requests")
BOOLEAN_FIELDS = ("success", "architectural_compliance", "task_success", "content_success", "procedure_applicable",
                  "procedure_compliance", "token_measurement_complete", "architectural_candidate_rejected")
FAILURE_CLASSES = ("technical_failure_or_interruption", "architectural_contract_violation", "invalid_or_missing_judgment",
                   "content_and_mandatory_evidence", "content_only", "mandatory_evidence_only", "unknown_or_other")
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
FIGURES = ("01_sucesso", "02_latencia_custo_sucesso", "03_categorias", "04_consistencia", "05_falhas")
WRITER_FILES = frozenset({
    "README.md", "RELATORIO.md", "units.csv", "units.jsonl", "architecture-summary.csv", "category-summary.csv",
    "difficulty-summary.csv", "scenario-metrics.csv", "scenario-measurements.csv", "paired-secondary-effects.csv",
    "measurement-distributions.csv", "failure-classes.csv", "quality-distributions.csv", "critical-flags.csv",
    "paired-success.csv", "phase-cost-summary.csv", "historical-comparison.csv", "provenance.json",
    "results-summary.json", "recheck-analysis.json", "resource-consumption.json",
} | {f"figures/{name}.{suffix}" for name, suffix in product(FIGURES, ("png", "svg"))})
SCOPE_PROBE_NAME = "scope-probe-summary.json"


def stamp(value):
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return timestamp


def optional_lines(path):
    return read_jsonl(path) if path.is_file() else []


def validate_dispatch(manifest):
    dispatch = manifest["generation_dispatch"]
    mode, workers = dispatch["mode"], dispatch["workers"]
    if type(workers) is not int or workers < 1:
        raise ValueError("Invalid generation dispatcher worker count")
    if mode == "sequential" and workers == 1:
        return mode, workers
    if mode == PARALLEL_DISPATCH and workers >= 3 and workers % 3 == 0:
        return mode, workers
    raise ValueError("Invalid dispatcher mode or worker count for complete architecture triplets")


def validate_plan(manifest, historical):
    if manifest["configuration"]["protocol"] != PROTOCOL or manifest["repetitions"] != 5:
        raise ValueError("Require the v4.4 protocol and five repetitions")
    if manifest["cases"] != historical["cases"] or manifest["cases_sha256"] != historical["cases_sha256"]:
        raise ValueError("The original 40 cases, references and order must match exactly")
    if len(manifest["cases"]) != 40 or manifest["experiment_id"] == historical["experiment_id"]:
        raise ValueError("Require a new experiment over the original 40 cases")
    validate_dispatch(manifest)
    if manifest["configuration"]["workflow_and_swarm_core"] != "architectural-comparison-v4.2":
        raise ValueError("The v4.2 comparator architectures must be preserved")
    judge = manifest["evaluation_plan"]
    old_judge = historical["evaluation_plan"]
    for key in ("model_id", "temperature", "max_tokens", "version", "configuration_sha256"):
        if judge[key] != old_judge[key]:
            raise ValueError(f"Frozen semantic judge changed: {key}")
    for key, old_value in historical["configuration"].items():
        if key != "protocol" and manifest["configuration"].get(key) != old_value:
            raise ValueError(f"Frozen generation parameter changed: {key}")
    plan = manifest["analysis_plan"]
    old_plan = historical["analysis_plan"]
    for key in ("scenario_unit", "repetitions_per_scenario_architecture", "architectures", "primary_denominator_per_architecture",
                "primary_outcome", "paired_primary", "bootstrap", "paired_test"):
        if plan[key] != old_plan[key]:
            raise ValueError(f"Frozen statistical plan changed: {key}")
    plan_time = stamp(plan["declared_at_utc"])
    if plan_time > stamp(manifest["created_at"]) or canonical_digest(plan) != manifest["analysis_plan_sha256"]:
        raise ValueError("Analysis plan timing or hash differs from the frozen collection manifest")
    cases = {case["id"]: case for case in manifest["cases"]}
    units = {unit["unit_id"]: unit for unit in manifest["order"]}
    triplet = lambda row: (row["scenario_id"], row["architecture"], row["repetition"])
    expected = set(product(cases, ARCHES, range(5)))
    if len(units) != len(expected) or len(manifest["order"]) != len(expected) or set(map(triplet, units.values())) != expected:
        raise ValueError("Require all 600 distinct planned combinations")
    if list(map(triplet, manifest["order"])) != list(map(triplet, historical["order"])):
        raise ValueError("The logical plan differs from the frozen v4.2 order")
    return cases, units


def verify_sequential(runs):
    previous_finish = None
    verified = 0
    for row in runs.values():
        if row.get("mode") != "live" or row.get("comparison_protocol") != PROTOCOL:
            raise ValueError("Run mode or protocol differs from the frozen design")
        if not row.get("started_at"):
            if row["success"]:
                raise ValueError("Completed run is missing its start timestamp")
            continue
        start, finish = stamp(row["started_at"]), stamp(row["finished_at"])
        if finish < start or previous_finish is not None and start < previous_finish:
            raise ValueError("Generation timestamps contradict sequential execution")
        previous_finish = finish
        verified += 1
    return verified


def verify_generation(folder, manifest, runs):
    mode, workers = validate_dispatch(manifest)
    planned = manifest["order"]
    report = {"mode": mode, "workers": workers, "waves": None, "wave_barriers_verified": None,
              "unit_timestamp_pairs_verified": None}
    if mode == "sequential":
        report["unit_timestamp_pairs_verified"] = verify_sequential(runs)
        return report

    first_launch = None
    previous_finish = None
    waves = 0
    attempt_ids = set()
    for offset in range(0, len(planned), workers):
        wave = planned[offset:offset + workers]
        waves += 1
        expected_size = len(wave)
        architecture_counts = Counter(unit["architecture"] for unit in wave)
        if expected_size % 3 or any(architecture_counts[arch] != expected_size // 3 for arch in ARCHES):
            raise ValueError("Wave does not contain balanced architecture triplets")
        for index in range(0, expected_size, 3):
            block = wave[index:index + 3]
            if len({(unit["scenario_id"], unit["repetition"]) for unit in block}) != 1 or {unit["architecture"] for unit in block} != set(ARCHES):
                raise ValueError("Wave split a planned scenario-repetition triplet")
        launches, finishes = [], []
        for unit in wave:
            unit_id = unit["unit_id"]
            row = runs[unit_id]
            if row.get("mode") != "live" or row.get("comparison_protocol") != PROTOCOL:
                raise ValueError("Run mode or protocol differs from the frozen design")
            launch = read_json(folder / unit_id / "launch.json")
            attempt_id = row["attempt_id"]
            if (not attempt_id or attempt_id in attempt_ids or launch["attempt_id"] != attempt_id
                    or launch["wave"] != waves or row["generation_wave"] != waves
                    or launch["wave_size"] != expected_size or row["generation_wave_size"] != expected_size):
                raise ValueError("Wave launch and terminal do not agree with the unique planned attempt")
            attempt_ids.add(attempt_id)
            started = stamp(launch["started_at"])
            finished = stamp(row["finished_at"])
            if row.get("collector_finished_at"):
                collector_finished = stamp(row["collector_finished_at"])
                if collector_finished < finished:
                    raise ValueError("Collector completion precedes the worker terminal timestamp")
                finished = collector_finished
            elif row.get("end_to_end_latency_ms") is not None:
                # Launch timestamp precedes the monotonic duration measurement.
                finished = max(finished, started + timedelta(milliseconds=row["end_to_end_latency_ms"]))
            if finished < started or (row.get("started_at") and stamp(row["started_at"]) < started):
                raise ValueError("Terminal timing contradicts launch evidence")
            launches.append(started)
            finishes.append(finished)
        earliest = min(launches)
        if first_launch is None:
            first_launch = earliest
        if previous_finish is not None and earliest < previous_finish:
            raise ValueError("Wave launched before the previous wave reached the barrier")
        previous_finish = max(finishes)
    if first_launch is None or first_launch < stamp(manifest["created_at"]):
        raise ValueError("Wave launch evidence precedes the frozen plan")
    report.update(waves=waves, wave_barriers_verified=waves - 1, unit_timestamp_pairs_verified=len(attempt_ids))
    return report


def parallel_amendment(manifest):
    if manifest["generation_dispatch"]["mode"] != PARALLEL_DISPATCH:
        return None
    amendment = manifest["analysis_plan"]["parallel_amendment"]
    units = amendment["previous_sequential_terminal_units"]
    evaluations = amendment["previous_sequential_evaluations"]
    if (amendment["requested_by_author_before_parallel_cohort"] is not True or type(units) is not int or units < 0
            or type(evaluations) is not int or not 0 <= evaluations <= units
            or amendment["reuse_previous_first_attempts"] is not False):
        raise ValueError("Parallel amendment does not preserve distinct first attempts")
    return {"prior_sequential_terminal_units_excluded": units, "prior_sequential_evaluations_excluded": evaluations,
            "included_prior_sequential_units": 0}


def judge_dispositions(folder, runs, rows, manifest):
    by_attempt = {row["attempt_id"]: row for row in runs.values()}
    if len(by_attempt) != len(runs):
        raise ValueError("Duplicate generation attempt identity")
    mapping = read_json(folder / "blind-mapping.json")
    available = {uid for uid, row in by_attempt.items() if (row.get("final_text") or "").strip()}
    if set(mapping.values()) != available or len(mapping) != len(available):
        raise ValueError("Blind mapping differs from canonical available responses")
    failures = optional_lines(folder / "evaluation-failures.jsonl")
    recheck_units = manifest["stability_recheck_plan"]["unit_ids"]
    if len(recheck_units) != 15 or len(set(recheck_units)) != 15 or not set(recheck_units) <= runs.keys():
        raise ValueError("Require the planned 15 distinct stability units")
    recheck_ids = {rid for rid, attempt in mapping.items() if by_attempt[attempt]["unit_id"] in recheck_units}
    selected = read_json(folder / "recheck-selection.json")
    if set(selected["response_ids"]) != recheck_ids or len(selected["response_ids"]) != len(recheck_ids):
        raise ValueError("Recheck selection replaced a frozen planned unit")
    if any(row["phase"] not in PHASES[1:] for row in failures):
        raise ValueError("Unexpected canonical evaluation failure phase")
    results = {}
    for phase, filename, targets in (("primary", "evaluations.jsonl", set(mapping)),
                                      ("recheck", "reevaluations.jsonl", recheck_ids)):
        valid = optional_lines(folder / filename)
        failed = [row for row in failures if row["phase"] == phase]
        ids = [row["response_id"] for row in (*valid, *failed)]
        if len(ids) != len(targets) or set(ids) != targets:
            raise ValueError(f"Incomplete, duplicated, or unplanned {phase} judge dispositions")
        results[phase] = {"targets": targets, "valid": {row["response_id"]: row for row in valid}, "failed": failed}
    by_response = {attempt: rid for rid, attempt in mapping.items()}
    for uid, row in rows.items():
        rid = by_response.get(runs[uid]["attempt_id"])
        primary = results["primary"]["valid"].get(rid)
        if row.get("response_id") != rid or row.get("evaluation") != (primary["evaluation"] if primary else None):
            raise ValueError("Aggregate differs from canonical primary assessment")
    return mapping, results


def audit_scope_events(events, runs):
    by_attempt = {row["attempt_id"]: row for row in runs.values()}
    if len(by_attempt) != len(runs):
        raise ValueError("Duplicate generation attempt identity")
    executed = defaultdict(set)
    rejected = defaultdict(set)
    rejected_responses = defaultdict(list)
    final_responses = set()
    contracts = defaultdict(list)
    for event in events:
        attempt = event["attempt_id"]
        row = by_attempt[attempt]
        family, name = event["eventFamily"], event["eventName"]
        if family == "tool" and name == "started":
            executed[attempt].add(event["payload"]["toolCallId"])
        elif family == "tool" and name == "rejected":
            payload = event["payload"]
            call_id = payload.get("toolCallId")
            if (row["architecture"] != ARCHES[0] or event.get("actorName") != "supervisor"
                    or event.get("status") != "failed" or payload.get("reason") != "outside_supervisor_turn_scope"
                    or not isinstance(call_id, str) or not call_id or call_id in rejected[attempt]):
                raise ValueError("Unverified or duplicate supervisor scope rejection")
            rejected[attempt].add(call_id)
        elif family == "response" and name == "final":
            final_responses.add(attempt)
        elif family == "response" and name == "rejected":
            rejected_responses[attempt].append(event)
        elif family == "architecture" and name == "contract":
            contracts[attempt].append(event["payload"])
    diagnostics = {}
    for attempt, row in by_attempt.items():
        if rejected[attempt] & executed[attempt]:
            raise ValueError("A rejected supervisor tool ID also appears in a tool start")
        count = len(rejected[attempt])
        if any(contract.get("scopeRejectedToolRequests", count) != count for contract in contracts[attempt]):
            raise ValueError("Supervisor scope rejection count differs from contract trace")
        candidates = rejected_responses[attempt]
        candidate_rejected = row.get("final_outcome") == "architectural_contract_failed"
        if candidate_rejected or candidates:
            candidate = candidates[0] if len(candidates) == 1 else {}
            payload = candidate.get("payload", {})
            if (not candidate_rejected or row["architecture"] != ARCHES[0] or row["architectural_compliance"] is not False
                    or attempt in final_responses or bool((row.get("final_text") or "").strip())
                    or candidate.get("actorName") != "supervisor" or candidate.get("status") != "failed"
                    or payload.get("architectureMode") != ARCHES[0] or not payload.get("violations")
                    or not isinstance(row.get("candidate_text"), str) or payload.get("candidateText") != row["candidate_text"]
                    or len(contracts[attempt]) != 1 or contracts[attempt][0].get("compliant") is not False
                    or contracts[attempt][0].get("violations") != payload["violations"]):
                raise ValueError("Architectural candidate rejection lacks a matching trace without a final response")
        diagnostics[attempt] = {"scope_rejected_tool_requests": count, "architectural_candidate_rejected": candidate_rejected}
    return diagnostics


def summarize_trace_issues(issues, runs_by_attempt, diagnostics):
    trace_issues = Counter()
    for issue in issues:
        attempt, reason = issue.get("attempt_id"), issue["reason"]
        run = runs_by_attempt.get(attempt)
        if run and reason in {f"{family} unresolved IDs" for family in ("model", "agent", "tool", "handoff")} and run["success"] is False:
            trace_issues["unterminated_event_ids_on_failed_attempt"] += 1
        elif run and reason == "missing successful-call token measurement" and run["token_measurement_complete"] is False:
            trace_issues["missing_token_measurement"] += 1
        elif run and reason == "missing terminal final event" and diagnostics[attempt]["architectural_candidate_rejected"]:
            trace_issues["verified_architectural_candidate_rejections_without_final"] += 1
        else:
            raise ValueError("Canonical analysis reports a structural integrity issue")
    return trace_issues


def physical_resources(folder, runs, mapping, rates, *, judging=None, judge_workers=1, events=None):
    by_attempt = {row["attempt_id"]: row for row in runs.values()}
    starts = defaultdict(list)
    terminals = defaultdict(list)
    phase_totals = defaultdict(list)
    usage_by_unit = {}
    seen_request = {}
    seen_provider = set()
    event_counts = Counter()
    latencies = defaultdict(list)

    def observe(phase, owner, arch, request, state, usage):
        group = phase, arch
        if not request:
            raise ValueError("Physical request identity is required")
        if state == "started":
            if request in seen_request:
                raise ValueError("Duplicate physical request identity")
            seen_request[request] = group, owner
            starts[group].append(request)
        elif state in {"completed", "failed"}:
            if seen_request.get(request) != (group, owner):
                raise ValueError("Physical terminal has no matching phase and owner")
            provider = (usage or {}).get("providerRequestId")
            if provider and provider in seen_provider:
                raise ValueError("Duplicate provider request identity")
            if provider:
                seen_provider.add(provider)
            for key in ("inputTokens", "outputTokens", "totalTokens"):
                value = (usage or {}).get(key)
                if value is not None and (type(value) is not int or value < 0):
                    raise ValueError("Invalid physical token measurement")
            terminals[group].append((request, state, usage))
        else:
            raise ValueError("Unexpected physical request state")

    unit_starts = defaultdict(list)
    unit_terminals = defaultdict(list)
    for event in read_jsonl(folder / "events.jsonl") if events is None else events:
        attempt = event["attempt_id"]
        row = by_attempt[attempt]
        if event["eventFamily"] != "model" or event["eventName"] not in {"started", "completed", "failed"}:
            continue
        payload = event["payload"]
        request, state, usage = payload["callId"], event["eventName"], payload.get("usage")
        observe("generation", attempt, row["architecture"], request, state, usage)
        if state == "started":
            unit_starts[attempt].append(request)
        else:
            unit_terminals[attempt].append((request, state, usage))
    for attempt, row in by_attempt.items():
        entry = ledger_summary(unit_starts[attempt], unit_terminals[attempt], rates["generation"])
        if row.get("model_requests") != entry["requests_started"]:
            raise ValueError("Physical requests do not reconcile with canonical run")
        if not entry["requests_started"]:
            entry["estimated_cost_usd"] = 0.0
        usage_by_unit[row["unit_id"]] = entry
    journal = optional_lines(folder / "judge-attempts.jsonl")
    judge_starts = defaultdict(list)
    judge_ends = {}
    for event in journal:
        phase = event["phase"]
        if phase not in PHASES[1:]:
            continue
        response, request, state = event["response_id"], event["attempt_id"], event["event"]
        arch = by_attempt[mapping[response]]["architecture"]
        observe(phase, response, arch, request, state, event.get("usage"))
        if state == "started":
            judge_starts[phase, response].append(event)
            event_counts[phase, "provider_format_repairs"] += event.get("format_repair") == 1
        else:
            if request in judge_ends:
                raise ValueError("Duplicate judge terminal")
            judge_ends[request] = event
            if event.get("latency_ms") is not None:
                latencies[phase, arch].append(event["latency_ms"])
            event_counts[phase, "locally_normalized"] += event.get("local_format_repair") is True
            event_counts[phase, "invalid_schema_outputs"] += event.get("valid") is False

    judge_order = []
    if judging is not None:
        for phase, records in judging.items():
            if {rid for p, rid in judge_starts if p == phase} != records["targets"]:
                raise ValueError("Canonical judge dispositions differ from the physical request set")
            for rid in records["targets"]:
                requests = judge_starts[phase, rid]
                if len(requests) > 2 or requests[0].get("format_repair") != 0 or (
                    len(requests) == 2 and (requests[1].get("format_repair") != 1
                    or requests[1].get("replacement_of") != requests[0]["attempt_id"]
                    or judge_ends.get(requests[0]["attempt_id"], {}).get("valid") is not False)
                ):
                    raise ValueError("Unexpected repeat judgment or format repair chain")
                judge_order.extend(requests)
            for rid, record in records["valid"].items():
                terminal = judge_ends.get(record["attempt_id"], {})
                if terminal.get("valid") is not True or terminal.get("response_id") != rid or terminal.get("phase") != phase:
                    raise ValueError("Canonical valid assessment lacks a matching durable valid output")
            for record in records["failed"]:
                rid = record["response_id"]
                requests = judge_starts[phase, rid]
                last = requests[-1]["attempt_id"]
                if record["attempt_id"] not in (None, last) or any(
                    judge_ends.get(request["attempt_id"], {}).get("valid") is True for request in requests
                ):
                    raise ValueError("Canonical unknown judgment conflicts with the physical ledger")
    judge_order.sort(key=lambda event: stamp(event["started_at"]))
    previous_finish = None
    verified = 0
    for event in judge_order:
        start = stamp(event["started_at"])
        if judge_workers == 1 and previous_finish and start < previous_finish:
            raise ValueError("Judge timestamps contradict sequential execution")
        measured = judge_ends.get(event["attempt_id"], {}).get("latency_ms")
        if measured is not None:
            # The journal stores provider-call duration and starts a few operations earlier.
            previous_finish = start + timedelta(milliseconds=measured)
            verified += judge_workers == 1

    report = {}
    for phase in PHASES:
        for arch in ("all", *ARCHES):
            keys = [(phase, a) for a in ARCHES if arch in ("all", a)]
            request_ids = [uid for key in keys for uid in starts[key]]
            ended = [terminal for key in keys for terminal in terminals[key]]
            entry = ledger_summary(request_ids, ended, rates[phase])
            if not request_ids and (phase == "generation" or judging is not None):
                entry.update(usage_complete=True, estimated_cost_usd=0.0)
            if phase != "generation":
                values = [latency for key in keys for latency in latencies[key]]
                q50, q95 = np.quantile(values, [.5, .95]).tolist() if values else (None, None)
                entry.update(known_request_latencies=len(values), latency_ms_p50=q50, latency_ms_p95=q95)
            phase_totals[phase].append({"phase": phase, "architecture": arch, **entry})
        report[phase] = {**phase_totals[phase][0], **{k: count for (p, k), count in event_counts.items() if p == phase}}
    return report, [entry for phase in PHASES for entry in phase_totals[phase]], usage_by_unit, verified, len(judge_order)


def safe_unit(row, case, cost):
    result = {key: row[key] for key in ("unit_id", "scenario_id", "architecture", "repetition")}
    result.update({key: case[key] for key in ("stratum", "difficulty")})
    result["status"] = row["status"]
    for key in ("unit_id", "scenario_id", "stratum", "difficulty", "status"):
        if not SAFE_ID.fullmatch(result[key]):
            raise ValueError("An experimental identifier is outside the safe export format")
    for key in BOOLEAN_FIELDS:
        result[key] = tri_state(row.get(key))
    for key in COUNT_FIELDS:
        value = row.get(key)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError(f"Invalid numeric metric: {key}")
        result[key] = value
    for key in ("latency_ms", "end_to_end_latency_ms"):
        value = row.get(key)
        if value is not None and (type(value) not in (int, float) or not np.isfinite(value) or value < 0):
            raise ValueError(f"Invalid latency: {key}")
        result[key] = value
    assessment = row.get("evaluation")
    result.update(failure_class=row["failure_class"], estimated_generation_cost_usd=cost["estimated_cost_usd"],
                  known_partial_estimated_generation_cost_usd=cost["known_partial_estimated_cost_usd"],
                  judge_schema_valid=assessment is not None, judge_internally_inconsistent=inconsistent_judgment(row))
    for dimension in DIMS:
        score = assessment["quality"][dimension] if assessment and not result["judge_internally_inconsistent"] else None
        if score is not None and (type(score) is not int or score not in range(1, 6)):
            raise ValueError("Invalid ordinal rubric value")
        result[f"judge_{dimension}"] = score
    return result


def paired_task(rows, plan):
    counts = defaultdict(Counter)
    for row in rows:
        counts[row["scenario_id"], row["architecture"]][row["task_success"]] += 1
    scenarios = sorted({row["scenario_id"] for row in rows})
    config = plan["bootstrap"], plan["paired_test"]
    paired = []
    for first, second in combinations(ARCHES, 2):
        deltas, lows, highs = [], [], []
        complete = 0
        for scenario in scenarios:
            a, b = counts[scenario, first], counts[scenario, second]
            delta = (b[True] - a[True]) / 5
            deltas.append(delta)
            lows.append(delta - a[None] / 5)
            highs.append(delta + b[None] / 5)
            complete += not (a[None] or b[None])
        paired.append({"architecture_a": first, "architecture_b": second,
                       **paired_success(deltas, seed=config[0]["seed"], bootstraps=config[0]["resamples"],
                                        permutations=config[1]["resamples"]),
                       "scenario_pairs_without_unknown": complete,
                       "all_scenarios_missing_lower_pp": float(np.mean(lows) * 100),
                       "all_scenarios_missing_upper_pp": float(np.mean(highs) * 100)})
    for row, adjusted in zip(paired, holm([row["p_unadjusted"] for row in paired]), strict=True):
        row["p_holm_three_comparisons"] = adjusted
    return paired


def secondary_exports(rows):
    by_scenario = defaultdict(list)
    for row in rows:
        by_scenario[row["scenario_id"], row["architecture"]].append(row)
    scenarios = []
    for (cid, architecture), units in sorted(by_scenario.items()):
        scenarios.append({"scenario_id": cid, "architecture": architecture, "planned": 5,
                          "task_successes": sum(row["task_success"] is True for row in units),
                          "task_unknown": sum(row["task_success"] is None for row in units),
                          **{f"{key}_median": med([row[key] for row in units]) for key in MEASUREMENTS}})
    by_key = {(row["scenario_id"], row["architecture"]): row for row in scenarios}
    contrasts = []
    for a, b in combinations(ARCHES, 2):
        for key in MEASUREMENTS:
            pairs = [(by_key[cid, a][f"{key}_median"], by_key[cid, b][f"{key}_median"])
                     for cid in sorted({row["scenario_id"] for row in rows})]
            known = [(va, vb) for va, vb in pairs if va is not None and vb is not None]
            contrasts.append({"architecture_a": a, "architecture_b": b, "metric": key, "paired_scenarios": len(known),
                              "median_paired_difference_b_minus_a": med([vb - va for va, vb in known]),
                              "median_paired_ratio_b_over_a": med([vb / va for va, vb in known if va])})
    distributions = []
    for arch, measure, completed in product(ARCHES, MEASUREMENTS, (True, False)):
        values = [row[measure] for row in rows if row["architecture"] == arch and row["success"] is completed
                  and row[measure] is not None]
        quantiles = np.quantile(values, [0, .25, .5, .75, .95, 1]).tolist() if values else [None] * 6
        distributions.append({"architecture": arch, "metric": measure,
                              "status_group": "technical_completed" if completed else "technical_failure",
                              "measured_n": len(values), "planned": 200,
                              **dict(zip(("min", "q25", "median", "q75", "p95", "max"), quantiles, strict=True))})
    return scenarios, contrasts, distributions


def report_text(data, tables):
    summaries = tables["architecture-summary.csv"]
    pairs = tables["paired-success.csv"]
    resources = tables["phase-cost-summary.csv"]
    recheck = data["recheck"]
    probe = data["scope_probe"]
    dispatch = data["provenance"]["generation_dispatch"]
    amendment = data["provenance"]["parallel_amendment"]
    generation_note = (
        f"A geração usou até {dispatch['workers']} processos em {dispatch['waves']} ondas de tripletas completas, "
        f"com {dispatch['wave_barriers_verified']} barreiras verificadas. A latência descreve a carga mista observada.\n\n"
        if dispatch["mode"] == PARALLEL_DISPATCH else "A geração foi executada em ordem sequencial.\n\n"
    )
    if amendment:
        generation_note += (
            f"O lote sequencial anterior terminou com {amendment['prior_sequential_terminal_units_excluded']} tentativas "
            f"e {amendment['prior_sequential_evaluations_excluded']} julgamentos. As 600 tentativas deste relatório pertencem "
            "ao novo lote paralelo, cujo plano foi congelado antes da geração.\n\n"
        )
    probe_note = (
        f"A sondagem sintética independente registrou {probe['out_of_scope_requests_rejected']} rejeição fora do escopo, "
        f"{probe['rejected_request_execution_count']} execuções da solicitação rejeitada e {probe['physical_requests']} "
        "requisições físicas. A sondagem fica separada do lote principal. [Resumo da sondagem](scope-probe-summary.json)\n\n"
        if probe else ""
    )
    return (
        "# Comparação arquitetural v4.4\n\n"
        "## Escopo e desenho\n\n"
        "Nova coleta de 600 tentativas nos mesmos 40 cenários derivados de conversas WhatsApp. "
        "Cada cenário recebe cinco repetições por condição. O cenário é a unidade pareada. "
        "A condição centralizada usa um supervisor que chama agentes especialistas como ferramentas e mantém a autoria final. "
        "Workflow e Swarm preservam as implementações v4.2. A referência de conteúdo, as fontes controladas e o julgador cego são os congelados. "
        "A análise e as conclusões de conteúdo são automáticas e provisórias. A avaliação humana da v4.4 permanece pendente.\n\n"
        + generation_note
        + f"O despacho do julgador após a geração usou até {data['provenance']['judge_workers']} processo(s). "
        "Os custos e tempos do julgamento ficam separados da geração.\n\n"
        "## Resultados e cobertura\n\n"
        + table(summaries, ["architecture", "planned", "technical_successes", "architectural_compliant", "architectural_unknown",
                            "task_successes", "task_failures", "task_unknown", "judge_schema_valid", "judge_valid_assessment"])
        + "\nA rejeição de uma chamada fora do escopo é medida separadamente do contrato da resposta. "
        "A auditoria conferiu que cada ID de chamada rejeitada ficou sem evento de início de ferramenta na mesma tentativa.\n\n"
        + table(summaries, ["architecture", "scope_rejected_tool_requests", "attempts_with_scope_rejections",
                            "architectural_violations", "architectural_candidates_rejected"])
        + "\nO primário exige conclusão técnica, conformidade arquitetural, conteúdo sob o instrumento congelado e evidência de consulta obrigatória. "
        "A proporção primária conta sucessos comprovados por 200 unidades planejadas e mantém falhas e desconhecidos separados. "
        "As tabelas incluem a taxa entre conhecidos e os limites para os resultados ausentes.\n\n"
        + table(pairs, ["architecture_a", "architecture_b", "paired_scenarios", "difference_pp_b_minus_a",
                        "bootstrap_95_low_pp", "bootstrap_95_high_pp", "p_holm_three_comparisons"])
        + "\nO contraste usa o número de sucessos comprovados em cinco tentativas por cenário. "
        "Os intervalos percentis marginais vêm de 20.000 reamostragens pareadas de cenários. "
        "A permutação bilateral pressupõe invariância conjunta à inversão de sinais e Holm cobre os três contrastes. "
        "A inferência é condicional à amostra conhecida. O CSV inclui limites para a atribuição dos desconhecidos.\n\n"
        + table(summaries, ["architecture", "content_successes", "content_evaluable", "mandatory_evidence_applicable",
                            "mandatory_evidence_compliant", "mandatory_evidence_evaluable", "complete_scenarios",
                            "pass_1_complete", "pass_5_complete"])
        + "\n## Medições e custos\n\n"
        "A latência do núcleo e a do coletor têm fronteiras diferentes. O coletor inclui o subprocesso e os arquivos locais. "
        "Os CSVs mostram distribuições por tentativa e quartis das medianas de cenários completos. "
        "As estimativas em USD usam uso físico e tarifas padrão. Uso parcial permanece explícito.\n\n"
        + table([row for row in resources if row["architecture"] == "all"],
                ["cohort", "phase", "requests_started", "requests_with_usage", "known_totalTokens", "estimated_cost_usd"])
        + "\n" + probe_note + "## Rechecagem e limites\n\n"
        + f"Houve {recheck['schema_valid_rechecks']}/15 rechecagens válidas, {recheck['known_composite_pairs']} pares conhecidos "
        f"e {recheck['known_composite_changes']} mudanças nesses pares. A rechecagem usa o mesmo julgador e preserva as decisões primárias.\n\n"
        + "A seleção foi intencional. Anexos são representados por metadados e as referências medem contratos técnicos. "
        "As conclusões se restringem aos cenários e configurações observados. Resultados v4.1, v4.2 e v4.3 permanecem como coortes distintas. "
        "Os arquivos deste pacote contêm métricas e metadados experimentais sanitizados.\n\n"
        + "\n".join(f"![{name}](figures/{name}.png)" for name in FIGURES) + "\n"
    )


def compare_history(summaries):
    history = []
    for version, name in (("v4.1", "matrix40-v1-final"), ("v4.2", "agents-as-tools-v42")):
        path = ROOT / "research-data/results" / name / "architecture-summary.csv"
        with path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        if len(rows) != 3 or {row["architecture"] for row in rows} != set(ARCHES):
            raise ValueError("Historical aggregate must contain the three distinct conditions")
        history.extend({"cohort": version, "architecture": row["architecture"],
                        "implementation": "single_agent_with_domain_tools" if version == "v4.1" and row["architecture"] == ARCHES[0]
                        else "supervisor_with_specialists_as_tools" if row["architecture"] == ARCHES[0] else row["architecture"],
                        **{key: int(row[key]) for key in ("planned", "task_successes", "task_unknown")}} for row in rows)
    return history + [{"cohort": "v4.4", "architecture": row["architecture"],
                       "implementation": "supervisor_with_specialists_as_tools" if row["architecture"] == ARCHES[0] else row["architecture"],
                       **{key: row[key] for key in ("planned", "task_successes", "task_unknown")}} for row in summaries]


def load_pilot(pilot, gate_path, manifest, manifest_sha256, rates):
    gate = read_json(gate_path)
    if gate.get("passed") is not True or gate.get("main_manifest_sha256") != manifest_sha256:
        raise ValueError("Engineering gate does not release this frozen main cohort")
    gate_info = {"passed": True, "gate_sha256": digest(gate_path)}
    if pilot is None:
        return [], gate_info
    pilot_manifest = read_json(pilot / "manifest.json")
    pilot_hash = digest(pilot / "manifest.json")
    if (pilot_manifest["configuration"] != manifest["configuration"]
            or gate.get("pilot_manifest_sha256", pilot_hash) != pilot_hash):
        raise ValueError("Engineering pilot did not pass under the frozen main configuration")
    planned = {row["unit_id"]: row for row in pilot_manifest["order"]}
    runs = index_records(read_jsonl(pilot / "runs.jsonl"), planned, complete=True)
    verify_generation(pilot, pilot_manifest, runs)
    mapping = read_json(pilot / "blind-mapping.json")
    _, phases, _, _, _ = physical_resources(pilot, runs, mapping, rates)
    return [{"cohort": "engineering_pilot", **row} for row in phases if row["requests_started"] or row["phase"] == "generation"], {
        **gate_info, "planned_units": len(runs), "manifest_sha256": pilot_hash,
    }


def load_scope_probe(path, rate):
    if not path.exists():
        return None
    probe = read_json(path)
    counts = ("out_of_scope_requests_rejected", "rejected_request_execution_count", "physical_requests", "input_tokens", "output_tokens")
    if (set(probe) != {*counts, "scope", "contract_passed"}
            or probe["scope"] != "separate synthetic engineering probe" or probe["contract_passed"] is not True
            or any(type(probe[field]) is not int or probe[field] < 0 for field in counts)
            or probe["out_of_scope_requests_rejected"] < 1 or probe["rejected_request_execution_count"] != 0
            or probe["physical_requests"] < 1):
        raise ValueError("Invalid sanitized engineering scope probe")
    return {**probe, "total_tokens": probe["input_tokens"] + probe["output_tokens"],
            "estimated_cost_usd": (probe["input_tokens"] * rate["input"] + probe["output_tokens"] * rate["output"]) / 1_000_000}


def export(cohort, output, historical_manifest, pricing_path, pilot, gate_path):
    manifest = read_json(cohort / "manifest.json")
    manifest_hash = digest(cohort / "manifest.json")
    historical = read_json(historical_manifest)
    cases, units = validate_plan(manifest, historical)
    amendment = parallel_amendment(manifest)
    runs = index_records(read_jsonl(cohort / "runs.jsonl"), units, complete=True)
    journal = index_records(read_jsonl(cohort / "attempts.jsonl"), units, complete=True)
    rows = index_records(read_jsonl(cohort / "aggregated-evaluations.jsonl"), units, complete=True)
    if list(runs) != list(units) or list(rows) != list(units) or runs != journal:
        raise ValueError("Canonical terminal run exports differ from frozen order or durable attempts")
    if any(rows[uid].get(key) != run.get(key) for uid, run in runs.items()
           for key in ("attempt_id", "final_text", "success", "architectural_compliance")):
        raise ValueError("Aggregated unit differs from canonical terminal generation")
    readiness = read_json(cohort / "readiness.json")
    events = read_jsonl(cohort / "events.jsonl")
    by_attempt = {row["attempt_id"]: row for row in runs.values()}
    diagnostics = audit_scope_events(events, runs)
    trace_issues = summarize_trace_issues(readiness["integrity_issues"], by_attempt, diagnostics)
    if readiness.get("attempts") != 600 or not readiness.get("calibration_passed"):
        raise ValueError("Canonical analysis has collection integrity or calibration issues")
    generation_audit = verify_generation(cohort, manifest, runs)
    generation_starts = [stamp(row["started_at"]) for row in runs.values() if row.get("started_at")]
    if not generation_starts or min(generation_starts) < stamp(manifest["created_at"]):
        raise ValueError("Generation timestamps precede the frozen plan")

    mapping, judgments = judge_dispositions(cohort, runs, rows, manifest)
    judge = read_json(cohort / "judge-config.json")
    config_hash = manifest["evaluation_plan"]["configuration_sha256"]
    if canonical_digest(judge) != config_hash:
        raise ValueError("Recorded judge differs from the frozen configuration")
    pricing = read_json(pricing_path)
    if pricing["currency"] != "USD" or pricing["region"] != manifest["configuration"]["region"] or pricing["region"] != judge["region"]:
        raise ValueError("Pricing region does not cover both frozen configurations")
    rate_table = pricing["rates_per_million_tokens"]
    rates = {"generation": rate_table["haiku_4_5"], "primary": rate_table["sonnet_4_5"], "recheck": rate_table["sonnet_4_5"]}
    judge_workers = manifest["evaluation_plan"]["dispatch_workers"]
    if type(judge_workers) is not int or not 1 <= judge_workers <= MAX_JUDGE_WORKERS:
        raise ValueError("Invalid v4.4 judge dispatcher worker count")
    for phase in PHASES[1:]:
        dispatch_path = cohort / "parallel-judging" / phase / "dispatch.json"
        if judge_workers > 1 or dispatch_path.exists():
            dispatch = read_json(dispatch_path)
            phase_summary = read_json(dispatch_path.with_name("summary.json"))
            if (dispatch["workers"] != judge_workers or phase_summary["unstarted_remaining"] != 0
                    or dispatch["manifest_sha256"] != manifest_hash or dispatch["configuration_sha256"] != config_hash
                    or dispatch["blind_responses_sha256"] != digest(cohort / "blind-responses.json")
                    or dispatch["planned_blind_responses"] != len(judgments[phase]["targets"])):
                raise ValueError("Judge dispatcher differs from frozen plan or still has unstarted work")
    resources, phases, costs, ordered_judgments, total_judgments = physical_resources(
        cohort, runs, mapping, rates, judging=judgments, judge_workers=judge_workers, events=events,
    )
    pilot_phases, pilot_info = load_pilot(pilot, gate_path, manifest, manifest_hash, rates)
    probe = load_scope_probe(cohort.parent / SCOPE_PROBE_NAME, rates["generation"])
    phase_rows = [{"cohort": "v4.4_main", **row} for row in phases] + pilot_phases
    safe = []
    for uid, row in rows.items():
        case = cases[row["scenario_id"]]
        row.update(diagnostics[row["attempt_id"]])
        if row["architectural_candidate_rejected"] and row["task_success"] is not False:
            raise ValueError("A verified architectural candidate rejection cannot have a known success or unknown task result")
        for field in ("stratum", "difficulty"):
            if row.get(field, case[field]) != case[field]:
                raise ValueError("Aggregate classification differs from the frozen case")
            row[field] = case[field]
        row["content_success"] = content_status(row)
        row["failure_class"] = failure_class(row)
        row["estimated_generation_cost_usd"] = costs[uid]["estimated_cost_usd"]
        if costs[uid]["usage_complete"]:
            for source, key in (("known_inputTokens", "input_tokens"), ("known_outputTokens", "output_tokens"),
                                ("known_totalTokens", "total_tokens")):
                if costs[uid][source] != row[key]:
                    raise ValueError("Physical usage differs from canonical unit measurements")
        safe.append(safe_unit(row, case, costs[uid]))

    all_rows = list(rows.values())
    summaries = [summary(arch, all_rows) for arch in ARCHES]
    for row in summaries:
        selected = [unit for unit in safe if unit["architecture"] == row["architecture"]]
        row.update(scope_rejected_tool_requests=sum(unit["scope_rejected_tool_requests"] for unit in selected),
                   attempts_with_scope_rejections=sum(unit["scope_rejected_tool_requests"] > 0 for unit in selected),
                   architectural_candidates_rejected=sum(unit["architectural_candidate_rejected"] for unit in selected))
    categories = [summary(arch, all_rows, category=category) for category in sorted({r["stratum"] for r in safe}) for arch in ARCHES]
    difficulties = [summary(arch, all_rows, difficulty=difficulty) for difficulty in sorted({r["difficulty"] for r in safe}) for arch in ARCHES]
    scenario_rows, secondary, distributions = secondary_exports(safe)
    failures = [{"architecture": arch, "failure_class": label, "count": sum(r["architecture"] == arch and r["failure_class"] == label for r in safe),
                 "denominator": 200} for arch, label in product(ARCHES, FAILURE_CLASSES)]
    if sum(row["count"] for row in failures) != sum(row["task_success"] is not True for row in safe):
        raise ValueError("Failure classes did not partition all nonsuccesses")
    quality = [{"architecture": arch, "dimension": dim, "score": score,
                "count": sum(row["architecture"] == arch and row[f"judge_{dim}"] == score for row in safe), "planned": 200}
               for arch, dim, score in product(ARCHES, DIMS, (1, 2, 3, 4, 5, None))]
    critical = [{"architecture": arch, "source": source, "violation": code, "overlapping": True, "planned": 200,
                 "assessed": sum(row["architecture"] == arch and row.get(source) is not None for row in all_rows),
                 "flagged": sum(row["architecture"] == arch and any(flag["violation_id"] == code
                                for flag in (row.get(source) or {}).get("critical_violations", [])) for row in all_rows)}
                for arch, source, code in product(ARCHES, ("evaluation", "objective_checks"), ("V1", "V2", "V3", "V4"))]
    paired = paired_task(safe, manifest["analysis_plan"])
    recheck_data = read_json(cohort / "recheck-analysis.json")
    changes = recheck_data["changes"]
    valid_rechecks = judgments["recheck"]["valid"]
    if recheck_data["planned"] != 15 or len(changes) != len(valid_rechecks) or {row["response_id"] for row in changes} != set(valid_rechecks):
        raise ValueError("Recheck analysis differs from canonical assessments")
    known_pairs = [row for row in changes if row["primary_evaluation_available"] and row["repeat_evaluation_available"]
                   and row["task_success_first"] is not None and row["task_success_second"] is not None]
    recheck = {"planned": 15, "available_responses": len(judgments["recheck"]["targets"]),
               "schema_valid_rechecks": len(valid_rechecks), "schema_valid_pairs": sum(row["critical_comparison_evaluable"] for row in changes),
               "known_composite_pairs": len(known_pairs), "known_composite_changes": sum(row["classification_changed"] for row in known_pairs),
               "critical_label_set_disagreements": sum(row["critical_disagreement"] is True for row in changes)}
    tables = {"units.csv": safe, "architecture-summary.csv": summaries, "category-summary.csv": categories,
              "difficulty-summary.csv": difficulties, "scenario-metrics.csv": scenario_rows,
              "scenario-measurements.csv": measurement_summary(safe, MEASUREMENTS), "paired-secondary-effects.csv": secondary,
              "measurement-distributions.csv": distributions, "failure-classes.csv": failures, "quality-distributions.csv": quality,
              "critical-flags.csv": critical, "paired-success.csv": paired, "phase-cost-summary.csv": phase_rows,
              "historical-comparison.csv": compare_history(summaries)}
    provenance = {"protocol": PROTOCOL, "dataset_version": manifest["dataset_version"], "manifest_sha256": manifest_hash,
                  "historical_manifest_sha256": digest(historical_manifest), "cases_sha256": manifest["cases_sha256"],
                  "analysis_plan_sha256": manifest["analysis_plan_sha256"], "analysis_plan_declared_at": manifest["analysis_plan"]["declared_at_utc"],
                  "exporter_sha256": digest(Path(__file__)), "pricing_sha256": digest(pricing_path),
                  "reused_v42_method_sha256": digest(Path(__file__).with_name("summarize_corrected_comparison.py")),
                  "generation_model_id": manifest["configuration"]["model_id"], "judge_model_id": judge["model_id"],
                  "region": judge["region"], "judge_configuration_sha256": config_hash,
                  "terminal_units": 600, "scenario_count": 40, "repetitions": 5,
                  "execution": "parallel_balanced_waves" if generation_audit["mode"] == PARALLEL_DISPATCH else "sequential",
                  "generation_dispatch": generation_audit, "parallel_amendment": amendment,
                  "judge_workers": judge_workers,
                  "generation_timestamp_pairs_checked": generation_audit["unit_timestamp_pairs_verified"],
                  "judge_timestamp_pairs_checked": ordered_judgments,
                  "judge_physical_requests": total_judgments, "engineering_pilot": pilot_info,
                  "trace_measurement_limitations": dict(trace_issues),
                  "raw_conversations_published": False, "human_review_performed": False}
    results = {"generated": 600, "human_validation_status": "pending", "human_review_performed": False,
               "responses_available": len(mapping), "primary_schema_valid": len(judgments["primary"]["valid"]),
               "responses_unavailable": 600 - len(mapping),
               "primary_invalid_or_missing": len(judgments["primary"]["failed"]),
               "primary_internally_inconsistent": sum(r["judge_internally_inconsistent"] for r in safe),
               "task_successes": sum(r["task_success"] is True for r in safe), "task_failures": sum(r["task_success"] is False for r in safe),
               "task_unknown": sum(r["task_success"] is None for r in safe), "architectures": summaries,
               "paired_success": paired, "recheck": recheck, "scope_probe": probe, "provenance": provenance}
    with new_directory(output) as stage:
        for name, values in tables.items():
            csvwrite(stage / name, values)
        (stage / "units.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in safe), encoding="utf-8")
        for name, values in (("provenance.json", provenance), ("results-summary.json", results), ("recheck-analysis.json", recheck),
                             ("resource-consumption.json", {**resources, "pricing": pricing, "scope": "main cohort physical requests"})):
            write_json_new(stage / name, values)
        if probe:
            write_json_new(stage / SCOPE_PROBE_NAME, probe)
        figures(stage, summaries, categories, failures, safe)
        (stage / "RELATORIO.md").write_text(report_text(results, tables), encoding="utf-8")
        (stage / "README.md").write_text("# Pacote de redação v4.4\n\n"
            "Comece por [RELATORIO.md](RELATORIO.md). `units.csv` e `units.jsonl` registram as 600 tentativas sanitizadas. "
            "Os resultados automáticos são provisórios. A revisão humana permanece pendente. "
            "O pacote de evidências restrito conserva os registros brutos.\n", encoding="utf-8")
        write_json_new(stage / "FILES.json", {str(path.relative_to(stage)): {"sha256": digest(path), "bytes": path.stat().st_size}
                       for path in sorted(stage.rglob("*")) if path.is_file()})
    return results


def writer_zip(output, destination):
    inventory = read_json(output / "FILES.json")
    if set(inventory) - {SCOPE_PROBE_NAME} != WRITER_FILES:
        raise ValueError("Writer export differs from the expected artifact allowlist")
    destination.parent.mkdir(parents=True, exist_ok=True)
    relative_result = Path("research-data/results/architectural-comparison-v44")
    safe_support = (Path("docs/tcc/state/evidence-gates.yml"), Path("experiments/architectural-comparison-v44/DATASET.md"),
                    Path("experiments/architectural-comparison-v44/README.md"), Path("experiments/architectural-comparison-v44/analysis-plan.json"))
    with NamedTemporaryFile(dir=destination.parent, prefix=".writer-v44-", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with ZipFile(temporary, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("LEIA-ME.md", "# Pacote de redação v4.4\n\n"
                "Comece pelo [relatório](research-data/results/architectural-comparison-v44/RELATORIO.md) e consulte "
                "as [600 tentativas sanitizadas](research-data/results/architectural-comparison-v44/units.csv). "
                "O [protocolo](experiments/architectural-comparison-v44/README.md) documenta a coleta.\n\n"
                "As conclusões de conteúdo são automáticas e provisórias. A revisão humana está pendente. "
                "A [política do manuscrito](docs/tcc/state/evidence-gates.yml) registra as autorizações aplicáveis.\n")
            for name, metadata in inventory.items():
                relative = Path(name)
                if relative.is_absolute() or ".." in relative.parts or relative.suffix not in {".md", ".csv", ".json", ".jsonl", ".png", ".svg"}:
                    raise ValueError("Unexpected writer archive member")
                path = output / relative
                if path.is_symlink() or path.stat().st_size != metadata["bytes"] or digest(path) != metadata["sha256"]:
                    raise ValueError("Export differs from writer archive inventory")
                archive.write(path, relative_result / relative)
            archive.write(output / "FILES.json", relative_result / "FILES.json")
            for relative in safe_support:
                path = ROOT / relative
                if path.is_file() and not path.is_symlink():
                    archive.write(path, relative)
        os.link(temporary, destination)
    finally:
        temporary.unlink()


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--historical-manifest", type=Path, default=HISTORICAL_MANIFEST)
    parser.add_argument("--pricing", type=Path, default=DEFAULT_PRICING)
    parser.add_argument("--pilot", type=Path)
    parser.add_argument("--engineering-gate", type=Path)
    parser.add_argument("--writer-zip", type=Path)
    args = parser.parse_args()
    if args.writer_zip and args.writer_zip.exists():
        parser.error("Writer ZIP already exists")
    gate = args.engineering_gate or args.cohort / "engineering-gate.json"
    result = export(args.cohort, args.output, args.historical_manifest, args.pricing, args.pilot, gate)
    if args.writer_zip:
        writer_zip(args.output, args.writer_zip)
    print(json.dumps({key: result[key] for key in ("generated", "task_successes", "task_failures", "task_unknown", "human_validation_status")}))


if __name__ == "__main__":
    main()
