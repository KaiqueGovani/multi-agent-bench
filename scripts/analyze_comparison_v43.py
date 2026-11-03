#!/usr/bin/env python3
"""Analyze v4.3 locally or verify v4.2 methods from the sanitized public export."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from itertools import combinations
import json
import math
import os
from pathlib import Path

import numpy as np

from human_review_v43 import (
    ARCHITECTURES, checked_sample, content_pass, digest, index_records, load_manifest,
    new_directory, read_json, read_jsonl, write_json_new,
)
from summarize_corrected_comparison import csvwrite, holm, ledger_summary, med, paired_success, priced


AUTOMATIC_PRIMARY = "automatic_content_pass"
HUMAN_PRIMARY = "human_consensus_content_pass"
SECONDARY = ("technical_completion", "architectural_compliance", "mandatory_consultation_compliance",
             "objective_critical_detected", "conjunctive_task_success")
QUALITY_DIMENSIONS = ("intent_adherence", "operational_correctness", "safety", "completeness", "clarity")
PHASES = ("generation", "primary", "recheck")
MODELS = {"generation": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
          "judge": "us.anthropic.claude-sonnet-4-5-20250929-v1:0"}
DEFAULT_PRICING = (Path(__file__).resolve().parents[1] / "experiments" /
                   "architectural-comparison-v42" / "pricing.json")


def tri_state(value):
    if value is not None and type(value) is not bool:
        raise ValueError("Expected a boolean or unknown disposition")
    return value


def automatic_content(row, case):
    evaluation = row.get("evaluation")
    if (not (row.get("final_text") or "").strip() or evaluation is None or row.get("judge_consistency_issue")
            or str(row.get("reason") or "").startswith("evaluator internal contradiction")):
        return None
    expected = {criterion["criterion_id"] for criterion in case["essential_requirements"]}
    assessed = {criterion["criterion_id"]: tri_state(criterion["met"]) for criterion in evaluation["criteria"]}
    if not expected or set(assessed) != expected or len(assessed) != len(evaluation["criteria"]):
        raise ValueError("Judgment criteria differ from the frozen case reference")
    observed = tri_state(evaluation.get("referral_recommendation_observed", evaluation.get("referral_observed")))
    return content_pass(list(assessed.values()), bool(evaluation["critical_violations"]),
                        case["professional_review_required"], observed,
                        insufficient=tri_state(evaluation["evidence_insufficient"]) is not False)


def conjunctive(values):
    if False in values:
        return False
    return None if None in values else True


def automated_rows(aggregates, cases, rates=None):
    rows = []
    for row in aggregates.values():
        case = cases[row["scenario_id"]]
        content = automatic_content(row, case)
        applicable = bool(case["required_evidence"])
        if row["procedure_applicable"] is not applicable:
            raise ValueError("Procedure applicability differs from the frozen case")
        technical = tri_state(row.get("success"))
        contract = tri_state(row.get("architectural_compliance"))
        procedure = tri_state(row.get("procedure_compliance")) if applicable else None
        objective = row.get("objective_checks")
        critical = bool(objective["critical_violations"]) if objective is not None and (row.get("final_text") or "").strip() else None
        composite = conjunctive([technical, contract, content, procedure if applicable else True,
                                 None if critical is None else not critical])
        cost = None
        if rates and row.get("token_measurement_complete") is True and not row.get("cache_usage_observed"):
            cost = priced(row.get("input_tokens"), row.get("output_tokens"), rates)
        rows.append({**{field: row.get(field) for field in ("unit_id", "scenario_id", "architecture", "repetition",
                     "latency_ms", "end_to_end_latency_ms", "total_tokens", "model_requests")},
                     "stratum": case["stratum"],
                     AUTOMATIC_PRIMARY: content, "technical_completion": technical, "architectural_compliance": contract,
                     "mandatory_consultation_applicable": applicable, "mandatory_consultation_compliance": procedure,
                     "objective_critical_detected": critical, "conjunctive_task_success": composite,
                     "estimated_generation_cost_usd": cost})
    return rows


def disposition(values):
    count = len(values)
    positive = sum(value is True for value in values)
    negative = sum(value is False for value in values)
    unknown = count - positive - negative
    known = positive + negative
    return {"planned_applicable": count, "positive": positive, "negative": negative, "unknown": unknown,
            "known": known, "rate_known": positive / known if known else None,
            "rate_lower": positive / count if count else None,
            "rate_upper": (positive + unknown) / count if count else None}


def summarize_outcomes(rows, metrics):
    summaries = []
    for architecture in ARCHITECTURES:
        selected = [row for row in rows if row["architecture"] == architecture]
        for metric in metrics:
            values = [row[metric] for row in selected if metric != "mandatory_consultation_compliance"
                      or row["mandatory_consultation_applicable"]]
            summaries.append({"architecture": architecture, "outcome": metric, "planned_all": len(selected),
                              **disposition(values)})
    return summaries


def summarize_strata(rows):
    return [{"stratum": stratum, **summary}
            for stratum in sorted({row["stratum"] for row in rows})
            for summary in summarize_outcomes([row for row in rows if row["stratum"] == stratum],
                                              (AUTOMATIC_PRIMARY, *SECONDARY))]


def quality_distribution(aggregates):
    results = []
    for architecture in ARCHITECTURES:
        rows = [row for row in aggregates.values() if row["architecture"] == architecture]
        for dimension in QUALITY_DIMENSIONS:
            scores = Counter(row["evaluation"]["quality"][dimension] if row.get("evaluation") is not None
                             and not row.get("judge_consistency_issue") else None for row in rows)
            if set(scores) - {None, 1, 2, 3, 4, 5}:
                raise ValueError("An automatic quality score is outside the frozen scale")
            results.append({"architecture": architecture, "dimension": dimension, "planned_units": len(rows),
                            "unknown": scores[None], "known": len(rows) - scores[None],
                            **{f"score_{score}": scores[score] for score in range(1, 6)}})
    return results


def scenario_groups(rows, metric):
    groups = defaultdict(list)
    for row in rows:
        groups[row["scenario_id"], row["architecture"]].append(row[metric])
    return groups


def contrast_rows(rows, metric, config, *, test):
    groups = scenario_groups(rows, metric)
    scenario_ids = sorted({row["scenario_id"] for row in rows})
    contrasts = []
    for first, second in combinations(ARCHITECTURES, 2):
        complete = []
        lower = []
        upper = []
        for scenario in scenario_ids:
            a = disposition(groups[scenario, first])
            b = disposition(groups[scenario, second])
            if a["planned_applicable"] != b["planned_applicable"] or not a["planned_applicable"]:
                raise ValueError("Unbalanced planned scenario pair")
            lower.append(b["rate_lower"] - a["rate_upper"])
            upper.append(b["rate_upper"] - a["rate_lower"])
            if not a["unknown"] and not b["unknown"]:
                complete.append((b["positive"] - a["positive"]) / a["planned_applicable"])
        result = {"outcome": metric, "architecture_a": first, "architecture_b": second,
                  "planned_paired_scenarios": len(scenario_ids), "paired_scenarios": len(complete),
                  "excluded_incomplete_scenarios": len(scenario_ids) - len(complete),
                  "all_scenarios_missing_lower_pp": float(np.mean(lower) * 100),
                  "all_scenarios_missing_upper_pp": float(np.mean(upper) * 100),
                  "difference_pp_b_minus_a": None, "bootstrap_95_low_pp": None, "bootstrap_95_high_pp": None,
                  "p_unadjusted": None, "p_holm_three_comparisons": None}
        if complete and test:
            result.update(paired_success(complete, seed=config["seed"], bootstraps=config["bootstrap_resamples"],
                                         permutations=config["permutation_resamples"]))
            result["actual_permutation_draws"] = (2 ** result["nonzero_scenarios"] if result["nonzero_scenarios"] <= 16
                                                   else config["permutation_resamples"])
        elif complete:
            values = np.asarray(complete)
            rng = np.random.default_rng(config["seed"])
            bootstrap = values[rng.integers(0, len(values), size=(config["bootstrap_resamples"], len(values)))].mean(axis=1)
            low, high = np.quantile(bootstrap, [.025, .975])
            result.update(difference_pp_b_minus_a=float(values.mean() * 100),
                          bootstrap_95_low_pp=float(low * 100), bootstrap_95_high_pp=float(high * 100))
        contrasts.append(result)
    if test:
        family = [row["p_unadjusted"] if row["p_unadjusted"] is not None else 1 for row in contrasts]
        for row, adjusted in zip(contrasts, holm(family), strict=True):
            if row["p_unadjusted"] is not None:
                row["p_holm_three_comparisons"] = adjusted
    return contrasts


def consistency(rows, metrics):
    results = []
    for metric in metrics:
        groups = scenario_groups(rows, metric)
        for architecture in ARCHITECTURES:
            values = [group for (_, arch), group in groups.items() if arch == architecture]
            complete = [group for group in values if None not in group]
            distribution = Counter(sum(value is True for value in group) for group in complete)
            repeats = len(values[0])
            results.append({"architecture": architecture, "outcome": metric, "planned_scenarios": len(values),
                            "complete_scenarios": len(complete), "planned_repetitions_per_scenario": repeats,
                            "all_pass_complete": distribution[repeats] / len(complete) if complete else None,
                            "all_pass_lower": sum(all(value is True for value in group) for group in values) / len(values),
                            "all_pass_upper": sum(False not in group for group in values) / len(values),
                            **{f"complete_scenarios_with_{count}_passes": distribution[count] for count in range(repeats + 1)}})
    return results


def measurement_summary(rows, metrics):
    results = []
    for metric in metrics:
        groups = scenario_groups(rows, metric)
        for architecture in ARCHITECTURES:
            values = [group for (_, arch), group in groups.items() if arch == architecture]
            medians = [med(group) for group in values if None not in group]
            quartiles = np.quantile(medians, [.25, .5, .75]).tolist() if medians else [None] * 3
            attempts = [value for group in values for value in group if value is not None]
            results.append({"architecture": architecture, "measurement": metric, "planned_scenarios": len(values),
                            "complete_scenarios": len(medians), "known_attempts": len(attempts),
                            "planned_attempts": sum(map(len, values)), **attempt_percentiles(attempts),
                            "q25_scenario_medians": quartiles[0], "median_scenario_medians": quartiles[1],
                            "q75_scenario_medians": quartiles[2]})
    return results


def attempt_percentiles(values):
    p50, p95 = np.quantile(values, [.5, .95]).tolist() if values else (None, None)
    return {"p50_known_attempts": p50, "p95_known_attempts": p95}


def phase_rates(cohort, manifest, pricing):
    configuration = manifest["configuration"]
    evaluation_plan = manifest["evaluation_plan"]
    if (pricing["currency"] != "USD" or pricing["region"] != configuration["region"]
            or configuration["model_id"] != MODELS["generation"] or evaluation_plan["model_id"] != MODELS["judge"]):
        raise ValueError("The rate table does not cover the frozen generation and judge configuration")
    rates = pricing["rates_per_million_tokens"]
    judge = rates["sonnet_4_5"]
    for phase in PHASES[1:]:
        config_path = cohort / "parallel-judging" / phase / "judge-config.json"
        if config_path.exists():
            config = read_json(config_path)
            if config["region"] != pricing["region"] or config["model_id"] != MODELS["judge"]:
                raise ValueError("The recorded judge configuration does not match the rate table")
    return {"generation": rates["haiku_4_5"], "primary": judge, "recheck": judge}


def coordination_counts(events):
    requests = set()
    terminals = {}
    messages = {}
    for event in events:
        family, name, payload = event["eventFamily"], event["eventName"], event["payload"]
        if family == "handoff" and name in {"requested", "completed", "failed"}:
            transfer = payload["transferId"]
            if name == "requested":
                if transfer in requests:
                    raise ValueError("Duplicate handoff request")
                requests.add(transfer)
            else:
                if transfer in terminals:
                    raise ValueError("Duplicate handoff terminal")
                terminals[transfer] = name
        if family == "communication" and name == "message":
            identity = payload.get("transferId") or payload.get("messageId") or event["externalEventId"]
            if not identity or identity in messages:
                raise ValueError("Duplicate or unidentified explicit communication")
            messages[identity] = payload.get("characters", 0)
    if set(terminals) - requests:
        raise ValueError("Handoff terminal without a request")
    return {"handoffs_requested": len(requests), "handoffs_completed": sum(value == "completed" for value in terminals.values()),
            "handoffs_failed": sum(value == "failed" for value in terminals.values()),
            "handoffs_without_terminal": len(requests) - len(terminals), "explicit_messages": len(messages),
            "explicit_message_characters": sum(messages.values()), "messages_linked_to_handoff": len(set(messages) & requests)}


def resource_reports(cohort, manifest, runs, rates):
    by_attempt = {row["attempt_id"]: row for row in runs.values()}
    if len(by_attempt) != len(runs):
        raise ValueError("Duplicate generation attempt identity")
    events_by_attempt = defaultdict(list)
    for event in read_jsonl(cohort / "events.jsonl"):
        events_by_attempt[event["attempt_id"]].append(event)
    if set(events_by_attempt) - set(by_attempt):
        raise ValueError("Generation event does not match a canonical attempt")
    starts = defaultdict(list)
    terminals = defaultdict(list)
    latencies = defaultdict(list)
    format_counts = defaultdict(Counter)
    coordination = {arch: Counter() for arch in ARCHITECTURES}
    provider_ids = set()
    request_owners = {}

    def physical_event(phase, arch, request, owner, state, usage, latency):
        group = (phase, arch)
        if state == "started":
            if request in request_owners:
                raise ValueError("Duplicate physical request")
            request_owners[request] = (group, owner)
            starts[group].append(request)
        elif state in {"completed", "failed"}:
            if request_owners.get(request) != (group, owner):
                raise ValueError("Physical terminal does not match its phase and owner")
            if isinstance(usage, dict):
                provider = usage.get("providerRequestId")
                if provider and provider in provider_ids:
                    raise ValueError("Duplicate provider request identity")
                if provider:
                    provider_ids.add(provider)
                if any(type(usage[key]) is not int or usage[key] < 0
                       for key in ("inputTokens", "outputTokens", "totalTokens") if usage.get(key) is not None):
                    raise ValueError("Physical token measurements must be nonnegative integers")
            terminals[group].append((request, state, usage))
            if latency is not None:
                latencies[group].append(latency)
        else:
            raise ValueError("Unknown physical request lifecycle event")

    for attempt_id, row in by_attempt.items():
        architecture = row["architecture"]
        events = events_by_attempt[attempt_id]
        coordination[architecture].update(coordination_counts(events))
        model_events = [event for event in events if event["eventFamily"] == "model"
                        and event["eventName"] in {"started", "completed", "failed"}]
        recorded = row.get("model_requests")
        if recorded is not None and recorded != sum(event["eventName"] == "started" for event in model_events):
            raise ValueError("Canonical run model request count differs from physical trace")
        for event in model_events:
            payload = event["payload"]
            physical_event("generation", architecture, payload["callId"], attempt_id, event["eventName"],
                           payload.get("usage"), payload.get("latencyMs"))

    mapping = read_json(cohort / "blind-mapping.json")
    available = {attempt_id for attempt_id, row in by_attempt.items() if (row.get("final_text") or "").strip()}
    if len(mapping) != len(available) or set(mapping.values()) != available:
        raise ValueError("Blind mapping differs from the available canonical responses")
    journal = cohort / "judge-attempts.jsonl"
    for event in read_jsonl(journal) if journal.exists() else []:
        phase = event["phase"]
        if phase not in PHASES[1:]:
            continue  # Calibration and connectivity are separate cohorts and scopes.
        owner = event["response_id"]
        arch = by_attempt[mapping[owner]]["architecture"]
        state = event["event"]
        physical_event(phase, arch, event["attempt_id"], owner, state, event.get("usage"), event.get("latency_ms"))
        if state == "started" and event.get("format_repair") == 1:
            format_counts[phase, arch]["provider_format_repair_requests"] += 1
        if state == "completed" and event.get("local_format_repair") is True:
            format_counts[phase, arch]["locally_normalized_outputs"] += 1
        if state == "completed" and event.get("valid") is False:
            format_counts[phase, arch]["schema_invalid_physical_outputs"] += 1

    report = []
    dispatch = {"generation": {"status": "canonical_runs_complete", **manifest["generation_dispatch"]}}
    for phase in PHASES[1:]:
        base = cohort / "parallel-judging" / phase
        status = base / "summary.json"
        state = read_json(status) if status.exists() else None
        dispatch[phase] = {"status": "complete" if state and state["unstarted_remaining"] == 0 else "pending_or_incomplete",
                           "workers": state["workers"] if state else None}
    for phase in PHASES:
        for arch in ARCHITECTURES:
            group = phase, arch
            accounting = ledger_summary(starts[group], terminals[group], rates[phase])
            phase_complete = dispatch[phase]["status"] in {"canonical_runs_complete", "complete"}
            if not phase_complete:
                accounting["estimated_cost_usd"] = None
            elif not starts[group] and (phase != "generation" or all(row.get("model_requests") == 0
                       for row in runs.values() if row["architecture"] == arch)):
                accounting.update(usage_complete=True, estimated_cost_usd=0.0)
            report.append({"phase": phase, "architecture": arch, "phase_status": dispatch[phase]["status"],
                           **accounting, "known_request_latencies": len(latencies[group]),
                           **{field: format_counts[group][field] if phase != "generation" else None
                              for field in ("provider_format_repair_requests", "locally_normalized_outputs",
                                            "schema_invalid_physical_outputs")},
                           **attempt_percentiles(latencies[group])})
    return report, [{"architecture": arch, **counts} for arch, counts in coordination.items()], dispatch


def human_readout(cohort, path, sample, automatic):
    report = read_json(path)
    expected = sample["selected_unit_ids"]
    identifiers = [row["unit_id"] for row in report["rows"]]
    if (report["version"] != "v43-attested-human-review-v1" or report["manifest_sha256"] != sample["manifest_sha256"]
            or report["plan_sha256"] != digest(cohort / "human-review-plan.json")
            or report["runs_sha256"] != digest(cohort / "runs.jsonl") or identifiers != expected):
        raise ValueError("Human review score file differs from the frozen sample or generation")
    automated = {row["unit_id"]: row for row in automatic}
    rows = []
    paired = 0
    agreement = 0
    counts = Counter()
    submitted = [0, 0]
    identity_hints = [0, 0]
    for row in report["rows"]:
        reviews = (row["reviewer_a"], row["reviewer_b"])
        labels = [review["content_pass"] if review is not None else None for review in reviews]
        labels = [tri_state(label) for label in labels]
        if not row["response_available"] and any(review is not None for review in reviews):
            raise ValueError("An unavailable response cannot have a human label")
        for index, review in enumerate(reviews):
            if review is not None:
                submitted[index] += 1
                identity_hints[index] += tri_state(review["identity_hint"]) is True
        known_pair = labels[0] is not None and labels[1] is not None
        agreement_label = labels[0] == labels[1] if known_pair else None
        counts[agreement_label] += 1
        expected_consensus = labels[0] if labels[0] is not None and labels[0] is labels[1] else None
        label = tri_state(row["consensus_content_pass"])
        if label is not expected_consensus or row["agreement"] is not agreement_label:
            raise ValueError("Human consensus does not match both known reviewer labels")
        model_label = automated[row["unit_id"]][AUTOMATIC_PRIMARY]
        if label is not None and model_label is not None:
            paired += 1
            agreement += label == model_label
        rows.append({**automated[row["unit_id"]], HUMAN_PRIMARY: label})
    totals = {"human_review_performed": any(submitted), "planned": len(rows),
              "available": sum(row["response_available"] for row in report["rows"]),
              "submitted_per_reviewer": submitted, "agreement": counts[True], "disagreement": counts[False],
              "unresolved_pair": counts[None]}
    if any(report[field] != count for field, count in totals.items()):
        raise ValueError("Human review totals do not match the submitted row decisions")
    return rows, {**totals, "identity_hints_per_reviewer": identity_hints,
                  "known_consensus_pairs_with_automatic": paired, "agreements_with_automatic": agreement}


def recheck_stability(cohort, manifest, aggregates, runs):
    path = cohort / "recheck-analysis.json"
    planned = manifest.get("stability_recheck_plan", {}).get("unit_ids", [])
    planned_set = set(planned)
    if len(planned) != len(planned_set) or planned_set - runs.keys():
        raise ValueError("Recheck plan includes duplicate or unplanned units")
    if not path.exists():
        return []
    data = read_json(path)
    selected = {row["response_id"]: row for uid, row in aggregates.items() if uid in planned_set and row.get("response_id")}
    changes = {row["response_id"]: row for row in data["changes"]}
    if data["planned"] != len(planned) or len(changes) != len(data["changes"]) or changes.keys() - selected.keys():
        raise ValueError("Stability changes differ from the frozen sample")
    results = []
    for arch in ARCHITECTURES:
        subset = [change for rid, change in changes.items() if selected[rid]["architecture"] == arch]
        known = [row for row in subset if row["task_success_first"] is not None and row["task_success_second"] is not None
                 and row["primary_evaluation_available"] and row["repeat_evaluation_available"]]
        results.append({"architecture": arch, "planned_units": sum(runs[uid]["architecture"] == arch for uid in planned),
                        "available_responses": sum(row["architecture"] == arch for row in selected.values()),
                        "schema_valid_pairs": sum(row["critical_comparison_evaluable"] for row in subset),
                        "known_legacy_composite_pairs": len(known),
                        "changed_legacy_composite_pairs": sum(row["classification_changed"] for row in known),
                        "critical_label_set_disagreements": sum(row["critical_disagreement"] is True for row in subset),
                        **{f"{dimension}_{suffix}": value for dimension in QUALITY_DIMENSIONS
                           for suffix, value in (("known_pairs", sum(row["score_changes"][dimension] is not None for row in subset)),
                                                 ("changed_pairs", sum(row["score_changes"][dimension] not in (None, 0) for row in subset)))}})
    return results


def report_cohort(cohort, output, human_report, pricing_path):
    manifest, cases, units = load_manifest(cohort)
    sample = checked_sample(cohort, manifest, cases, units)
    runs = index_records(read_jsonl(cohort / "runs.jsonl"), units, complete=True)
    aggregates = index_records(read_jsonl(cohort / "aggregated-evaluations.jsonl"), units, complete=True)
    if any(aggregates[uid]["attempt_id"] != run["attempt_id"] or aggregates[uid].get("final_text") != run.get("final_text")
           for uid, run in runs.items()):
        raise ValueError("Aggregate does not match canonical generation")
    rates = phase_rates(cohort, manifest, read_json(pricing_path))
    resources, coordination, dispatch = resource_reports(cohort, manifest, runs, rates)
    stability = recheck_stability(cohort, manifest, aggregates, runs)
    automatic = automated_rows(aggregates, cases, rates["generation"])
    config = manifest["analysis_plan"]["paired_analysis"]
    automatic_summary = summarize_outcomes(automatic, (AUTOMATIC_PRIMARY, *SECONDARY))
    automatic_contrasts = contrast_rows(automatic, AUTOMATIC_PRIMARY, config, test=True)
    measurements = measurement_summary(automatic, ("latency_ms", "end_to_end_latency_ms", "total_tokens", "model_requests",
                                                    "estimated_generation_cost_usd"))
    human = None
    human_summary = []
    human_contrasts = []
    if human_report:
        human_rows, human = human_readout(cohort, human_report, sample, automatic)
        human_summary = summarize_outcomes(human_rows, (HUMAN_PRIMARY,))
        human_contrasts = contrast_rows(human_rows, HUMAN_PRIMARY, config, test=False)
    human_status = "pending"
    if human and human["human_review_performed"]:
        human_status = "completed_selected_sample" if human["agreement"] == human["planned"] else "partial_or_unresolved_selected_sample"
    data = {"protocol": manifest["configuration"]["protocol"], "manifest_sha256": sample["manifest_sha256"],
            "analysis_plan_sha256": manifest["analysis_plan_sha256"], "tool_sha256": digest(Path(__file__)),
            "reused_v42_method_sha256": digest(Path(__file__).with_name("summarize_corrected_comparison.py")),
            "dispatch": dispatch, "measurement_boundaries": manifest["measurement_boundaries"],
            "analysis_unit": "scenario", "planned_units": len(units), "scenario_count": len(cases),
            "repetitions": manifest["repetitions"], "automatic_scope": "provisional full-cohort automated content assessment",
            "human_validation_status": human_status, "human_planned_units": len(sample["selected_unit_ids"]),
            "human": human, "automatic_outcomes": automatic_summary, "automatic_primary_contrasts": automatic_contrasts,
            "human_outcomes": human_summary, "human_descriptive_contrasts": human_contrasts,
            "pricing_sha256": digest(pricing_path), "pricing_rates_usd_per_million": rates,
            "pricing_scope": "main cohort, physical requests, standard USD estimate; excludes API, pilot and calibration",
            "resources_by_phase_and_architecture": resources, "coordination_by_architecture": coordination,
            "scenario_measurements": measurements, "recheck_stability_descriptive": stability}
    with new_directory(output) as stage:
        write_json_new(stage / "summary.json", data)
        csvwrite(stage / "automatic-outcomes.csv", automatic_summary)
        csvwrite(stage / "automatic-paired-content.csv", automatic_contrasts)
        csvwrite(stage / "automatic-outcomes-by-stratum.csv", summarize_strata(automatic))
        csvwrite(stage / "automatic-quality-rubric.csv", quality_distribution(aggregates))
        csvwrite(stage / "scenario-consistency.csv", consistency(automatic, (AUTOMATIC_PRIMARY, "conjunctive_task_success")))
        csvwrite(stage / "scenario-measurements.csv", measurements)
        csvwrite(stage / "resources-by-phase-and-architecture.csv", resources)
        csvwrite(stage / "coordination-by-architecture.csv", coordination)
        if stability:
            csvwrite(stage / "recheck-stability-descriptive.csv", stability)
        if human_summary:
            csvwrite(stage / "human-selected-outcomes.csv", human_summary)
            csvwrite(stage / "human-selected-paired-descriptive.csv", human_contrasts)
        (stage / "RELATORIO.md").write_text(readout(data), encoding="utf-8")
    return data


def readout(data):
    def number(value, digits=2):
        return "N/D" if value is None else f"{value:.{digits}f}"

    lines = ["# Comparação v4.3", "", "## Resultado automático provisório", "",
             f"Foram analisadas {data['planned_units']} unidades em {data['scenario_count']} cenários, "
             f"com {data['repetitions']} repetições por condição.",
             "O desfecho primário avalia requisitos essenciais, recomendação profissional obrigatória e violações críticas no conteúdo da resposta.",
             "Conclusão técnica, contrato arquitetural, consulta obrigatória e sucesso composto são medidas separadas.",
             "", "| Condição | Conteúdo aprovado | Conhecido | Desconhecido | Planejado |", "|---|---:|---:|---:|---:|"]
    for row in data["automatic_outcomes"]:
        if row["outcome"] == AUTOMATIC_PRIMARY:
            lines.append(f"| {row['architecture']} | {row['positive']} | {row['known']} | {row['unknown']} | {row['planned_all']} |")
    lines += ["", "| A | B | Cenários completos | B − A (pp) | IC95% (pp) | p Holm | Limites com desconhecidos (pp) |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for row in data["automatic_primary_contrasts"]:
        lines.append(f"| {row['architecture_a']} | {row['architecture_b']} | {row['paired_scenarios']}/{row['planned_paired_scenarios']} "
                     f"| {number(row['difference_pp_b_minus_a'])} | {number(row['bootstrap_95_low_pp'])} a {number(row['bootstrap_95_high_pp'])} "
                     f"| {number(row['p_holm_three_comparisons'], 4)} | {number(row['all_scenarios_missing_lower_pp'])} a "
                     f"{number(row['all_scenarios_missing_upper_pp'])} |")
    lines += ["", "As comparações agrupam as repetições dentro de cada cenário. Os intervalos percentis são marginais e condicionais à amostra.",
              "A permutação inverte os sinais das diferenças por cenário e usa a média das diferenças como estatística. "
              "O teste pressupõe invariância conjunta a essas inversões sob a hipótese nula. Holm corrige os três contrastes primários.",
              "Os CSVs incluem os desfechos secundários e as distribuições ordinais por dimensão. As comparações por estrato são descritivas.",
              "", "## Tempo e recursos do lote", "",
              f"Geração em carga mista com até {data['dispatch']['generation']['workers']} processos por onda. "
              "As latências p50 e p95 usam tentativas com tempo medido. O arquivo de medições também inclui quartis das medianas de cenários completos.",
              "", "| Condição | Medida | Tentativas medidas | p50 (ms) | p95 (ms) |", "|---|---|---:|---:|---:|"]
    for row in data["scenario_measurements"]:
        if row["measurement"] in {"latency_ms", "end_to_end_latency_ms"}:
            label = "núcleo" if row["measurement"] == "latency_ms" else "coletor"
            lines.append(f"| {row['architecture']} | {label} | {row['known_attempts']}/{row['planned_attempts']} "
                         f"| {number(row['p50_known_attempts'])} | {number(row['p95_known_attempts'])} |")
    lines += ["", "| Fase | Condição | Requisições com uso | Tokens conhecidos | Estimativa integral (USD) |",
              "|---|---|---:|---:|---:|"]
    phase_names = {"generation": "Geração", "primary": "Julgamento", "recheck": "Rechecagem"}
    for row in data["resources_by_phase_and_architecture"]:
        lines.append(f"| {phase_names[row['phase']]} | {row['architecture']} | {row['requests_with_usage']}/{row['requests_started']} "
                     f"| {row['known_totalTokens'] if row['requests_with_usage'] or row['usage_complete'] else 'N/D'} "
                     f"| {number(row['estimated_cost_usd'], 4)} |")
    lines += ["", "As estimativas usam as tarifas geográficas padrão e os eventos de requisições físicas. O CSV separa parcelas conhecidas e totais indisponíveis.",
              "A contagem de transferências usa um ID por solicitação de handoff. O CSV de coordenação mostra as mensagens vinculadas separadamente.", ""]
    if data["recheck_stability_descriptive"]:
        lines.extend(["## Estabilidade do julgador", "", "| Condição | Pares válidos no schema | Pares com composto conhecido | Mudanças |",
                      "|---|---:|---:|---:|"])
        for row in data["recheck_stability_descriptive"]:
            lines.append(f"| {row['architecture']} | {row['schema_valid_pairs']}/{row['planned_units']} "
                         f"| {row['known_legacy_composite_pairs']} | {row['changed_legacy_composite_pairs']} |")
        lines += ["", "A rechecagem repete o julgador no subconjunto congelado. A tabela usa o desfecho composto anterior. "
                  "O CSV inclui mudanças por dimensão e divergências nas violações críticas.", ""]
    lines += ["## Revisão humana da amostra cega", ""]
    if data["human_validation_status"] == "pending":
        lines.append(f"Pendente de revisão humana independente nas {data['human_planned_units']} unidades pré-selecionadas.")
    else:
        human = data["human"]
        lines.append(f"Foram recebidas avaliações atestadas de dois revisores na amostra fixa. "
                     f"Há {human['agreement']} consensos conhecidos em {human['planned']} unidades planejadas, "
                     f"{human['disagreement']} discordâncias e {human['unresolved_pair']} pares sem duas decisões conhecidas.")
        lines.append("A comparação humana é descritiva na amostra selecionada. O resultado automático do lote integral permanece separado.")
    lines += ["", "O benchmark emprega referências técnicas controladas. A validade clínica e a generalização para atendimento real permanecem em aberto.", ""]
    return "\n".join(lines)


def audit_v42(source, output):
    units = read_jsonl(source / "units.jsonl")
    key = lambda row: (row["scenario_id"], row["architecture"], row["repetition"])
    scenarios = {row["scenario_id"] for row in units}
    expected = {(scenario, architecture, repeat) for scenario in scenarios for architecture in ARCHITECTURES for repeat in range(5)}
    if len(units) != 600 or len(scenarios) != 40 or set(map(key, units)) != expected:
        raise ValueError("Expected the original 600 complete v4.2 planned units")
    if any(type(row["task_success"]) is not bool for row in units):
        raise ValueError("This cross-check requires the observed complete v4.2 dispositions")
    with (source / "paired-success.csv").open(newline="", encoding="utf-8") as stream:
        published = {(row["architecture_a"], row["architecture_b"]): row for row in csv.DictReader(stream)}
    config = {"seed": 20261011, "bootstrap_resamples": 20000, "permutation_resamples": 99999}
    contrasts = contrast_rows(units, "task_success", config, test=True)
    fields = ("difference_pp_b_minus_a", "bootstrap_95_low_pp", "bootstrap_95_high_pp", "p_unadjusted", "p_holm_three_comparisons")
    for row in contrasts:
        original = published[row["architecture_a"], row["architecture_b"]]
        if int(original["paired_scenarios"]) != row["paired_scenarios"] or any(
            not math.isclose(row[field], float(original[field]), rel_tol=1e-10, abs_tol=1e-10) for field in fields
        ):
            raise ValueError("Recomputed v4.2 contrast differs from the published table")
    write_json_new(output, {"audit": "read-only v4.2 method reproduction", "paired_table_reproduced": True,
                           "units_sha256": digest(source / "units.jsonl"), "paired_sha256": digest(source / "paired-success.csv"),
                           "contrasts": contrasts, "scenario_consistency": consistency(units, ("task_success",)),
                           "scenario_latency_quartiles": measurement_summary(units, ("latency_ms", "end_to_end_latency_ms"))})


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    report = commands.add_parser("report")
    report.add_argument("--cohort", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True)
    report.add_argument("--human-report", type=Path)
    report.add_argument("--pricing", type=Path, default=DEFAULT_PRICING)
    audit = commands.add_parser("audit-v42")
    audit.add_argument("--source", type=Path, required=True)
    audit.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "audit-v42":
        audit_v42(args.source, args.output)
        print("v4.2 paired contrasts reproduced")
    else:
        data = report_cohort(args.cohort, args.output, args.human_report, args.pricing)
        print(json.dumps({"planned_units": data["planned_units"], "human_validation_status": data["human_validation_status"]}))


if __name__ == "__main__":
    main()
