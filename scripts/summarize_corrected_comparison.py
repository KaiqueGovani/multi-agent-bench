#!/usr/bin/env python3
"""Sanitized v4.2 export; scenario-cluster analysis and physical-request costs.

Run with the existing research-data/local/figures-env Python. Raw responses,
judgments, source arguments and trajectory examples stay in the private cohort.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import statistics

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARCHES = ("centralized_orchestration", "structured_workflow", "decentralized_swarm")
LABELS = ("Supervisor + especialistas", "Workflow", "Swarm")
COLORS = ("#2563eb", "#d97706", "#059669")
DIMS = ("intent_adherence", "operational_correctness", "safety", "completeness", "clarity")
SEED = 20261011


def read(path):
    return json.loads(path.read_text())


def lines(path):
    return [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csvwrite(path, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def med(values):
    known = [v for v in values if v is not None]
    return statistics.median(known) if known else None


def holm(values):
    adjusted = [None] * len(values)
    previous = 0.0
    for rank, i in enumerate(sorted(range(len(values)), key=lambda k: values[k])):
        previous = max(previous, min(1.0, (len(values) - rank) * values[i]))
        adjusted[i] = previous
    return adjusted


def paired_success(differences, *, seed=SEED, bootstraps=20000, permutations=99999):
    """Paired whole-scenario bootstrap and two-sided sign permutation."""
    delta = np.asarray(differences, dtype=float)
    if len(delta) == 0:
        raise ValueError("Paired scenario differences are required")
    rng = np.random.default_rng(seed)
    boots = delta[rng.integers(0, len(delta), size=(bootstraps, len(delta)))].mean(axis=1)
    low, high = np.quantile(boots, [.025, .975])
    nonzero = delta[delta != 0]
    observed = abs(float(nonzero.sum()))
    if len(nonzero) <= 16:
        statistics_ = [abs(float(np.dot(signs, nonzero))) for signs in itertools.product((-1, 1), repeat=len(nonzero))]
        p = sum(v >= observed - 1e-12 for v in statistics_) / len(statistics_)
        method = "exact paired sign permutation"
    else:
        rng = np.random.default_rng(seed)
        extreme = 0
        for start in range(0, permutations, 4096):
            count = min(4096, permutations - start)
            simulated = abs(rng.choice((-1, 1), size=(count, len(nonzero))) @ nonzero)
            extreme += int(np.count_nonzero(simulated >= observed - 1e-12))
        p = (extreme + 1) / (permutations + 1)
        method = "Monte Carlo paired sign permutation; plus-one correction"
    return {"paired_scenarios": len(delta), "difference_pp_b_minus_a": float(delta.mean() * 100),
            "bootstrap_95_low_pp": float(low * 100), "bootstrap_95_high_pp": float(high * 100),
            "p_unadjusted": p, "nonzero_scenarios": len(nonzero), "method": method,
            "seed": seed, "bootstrap_resamples": bootstraps, "permutation_resamples": permutations}


def inconsistent_judgment(row):
    return bool(row.get("judge_consistency_issue")) or row.get("reason", "").startswith("evaluator internal contradiction")


def content_status(row):
    # Content is independent of the new architectural gate and objective consultation.
    evaluation = row.get("evaluation")
    if evaluation is None:
        return None
    if inconsistent_judgment(row):
        return None
    if evaluation.get("critical_violations") or any(c["met"] is False for c in evaluation["criteria"]):
        return False
    if evaluation.get("evidence_insufficient") or any(c["met"] is None for c in evaluation["criteria"]):
        return None
    return True


def failure_class(row):
    if row["task_success"] is True:
        return "success"
    if not row.get("success"):
        return "technical_failure_or_interruption"
    if row.get("architectural_compliance") is False:
        return "architectural_contract_violation"
    if row.get("evaluation") is None or inconsistent_judgment(row):
        return "invalid_or_missing_judgment"
    content = content_status(row) is False or bool(row["objective_checks"]["critical_violations"])
    procedure = any(e["met"] is False for e in row["objective_checks"]["required_evidence"])
    if content and procedure:
        return "content_and_mandatory_evidence"
    if content:
        return "content_only"
    if procedure:
        return "mandatory_evidence_only"
    return "unknown_or_other"


def priced(input_tokens, output_tokens, rates):
    if input_tokens is None or output_tokens is None:
        return None
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000


def ledger_summary(starts, terminals, rate):
    if len(starts) != len(set(starts)) or len(terminals) != len({x[0] for x in terminals}):
        raise ValueError("Duplicate physical request IDs; cannot price safely")
    if {x[0] for x in terminals} - set(starts):
        raise ValueError("Orphan terminal physical request IDs")
    known = [(uid, usage) for uid, status, usage in terminals
             if isinstance(usage, dict) and all(usage.get(k) is not None for k in ("inputTokens", "outputTokens", "totalTokens"))]
    for _, usage in known:
        if usage["totalTokens"] != usage["inputTokens"] + usage["outputTokens"]:
            raise ValueError("Physical token total does not equal input plus output")
    cache = any(any(u.get(k, 0) for k in ("cacheReadInputTokens", "cacheWriteInputTokens")) for _, u in known)
    totals = {key: sum(u[key] for _, u in known) for key in ("inputTokens", "outputTokens", "totalTokens")}
    complete = bool(starts) and set(starts) == {uid for uid, _ in known} and not cache
    estimate = priced(totals["inputTokens"], totals["outputTokens"], rate)
    return {"requests_started": len(starts), "requests_terminal": len(terminals),
            "requests_with_usage": len(known), "requests_failed": sum(s != "completed" for _, s, _ in terminals),
            "usage_complete": complete, "cache_usage_observed": cache,
            **{"known_" + k: v for k, v in totals.items()},
            "estimated_cost_usd": estimate if complete else None,
            "known_partial_estimated_cost_usd": estimate if known and not cache else None}


def generation_resources(folder, rates):
    model = [e for e in lines(folder / "events.jsonl") if e["eventFamily"] == "model"]
    return ledger_summary([e["payload"]["callId"] for e in model if e["eventName"] == "started"],
                          [(e["payload"]["callId"], e["eventName"], e["payload"].get("usage"))
                           for e in model if e["eventName"] in {"completed", "failed"}], rates)


def judgments_resources(folder, phase, rates):
    events = [e for e in lines(folder / "judge-attempts.jsonl") if e["phase"] == phase]
    return ledger_summary([e["attempt_id"] for e in events if e["event"] == "started"],
                          [(e["attempt_id"], e["event"], e.get("usage"))
                           for e in events if e["event"] in {"completed", "failed"}], rates)


def summary(arch, rows, *, category="all", difficulty="all"):
    rr = [r for r in rows if r["architecture"] == arch
          and (category == "all" or r["stratum"] == category)
          and (difficulty == "all" or r["difficulty"] == difficulty)]
    known = sum(r["task_success"] is not None for r in rr)
    successes = sum(r["task_success"] is True for r in rr)
    case_ids = sorted({r["scenario_id"] for r in rr})
    complete = [[r["task_success"] for r in rr if r["scenario_id"] == cid] for cid in case_ids]
    complete = [v for v in complete if len(v) == 5 and all(x is not None for x in v)]
    result = {"architecture": arch, "category": category, "difficulty": difficulty, "planned": len(rr),
              "technical_successes": sum(r.get("success", False) for r in rr),
              "architectural_compliant": sum(r.get("architectural_compliance") is True for r in rr),
              "architectural_violations": sum(r.get("architectural_compliance") is False for r in rr),
              "architectural_unknown": sum(r.get("architectural_compliance") is None for r in rr),
              "task_successes": successes, "task_failures": sum(r["task_success"] is False for r in rr),
              "task_unknown": len(rr) - known, "observed_success_rate": successes / len(rr) if rr else None,
              "known_only_success_rate": successes / known if known else None,
              "content_successes": sum(content_status(r) is True for r in rr),
              "content_evaluable": sum(content_status(r) is not None for r in rr),
              "mandatory_evidence_applicable": sum(r["procedure_applicable"] for r in rr),
              "mandatory_evidence_compliant": sum(r["procedure_applicable"] and r["procedure_compliance"] is True for r in rr),
              "mandatory_evidence_evaluable": sum(r["procedure_applicable"] and r["procedure_compliance"] is not None for r in rr),
              "judge_schema_valid": sum(r.get("evaluation") is not None for r in rr),
              "judge_internally_inconsistent": sum(inconsistent_judgment(r) for r in rr),
              "judge_valid_assessment": sum(r.get("evaluation") is not None and not inconsistent_judgment(r) for r in rr),
              "judge_invalid_or_missing": sum(r.get("evaluation") is None or inconsistent_judgment(r) for r in rr),
              "complete_scenarios": len(complete), "scenarios": len(case_ids),
              "pass_1_complete": statistics.mean(sum(v) / 5 for v in complete) if complete else None,
              "pass_5_complete": statistics.mean(all(v) for v in complete) if complete else None,
              "estimated_generation_cost_usd": sum(r["estimated_generation_cost_usd"] for r in rr) if all(r["estimated_generation_cost_usd"] is not None for r in rr) else None}
    result.update(pass_1_lower=successes / len(rr) if rr else None,
                  pass_1_upper=(successes + len(rr) - known) / len(rr) if rr else None,
                  pass_5_lower=sum(all(r["task_success"] is True for r in rr if r["scenario_id"] == cid) for cid in case_ids) / len(case_ids) if case_ids else None,
                  pass_5_upper=sum(not any(r["task_success"] is False for r in rr if r["scenario_id"] == cid) for cid in case_ids) / len(case_ids) if case_ids else None)
    for count in range(6):
        result[f"complete_scenarios_with_{count}_successes"] = sum(sum(v) == count for v in complete)
    cost = result["estimated_generation_cost_usd"]
    result["estimated_cost_per_observed_task_success_usd"] = cost / successes if cost is not None and successes else None
    for key in ("latency_ms", "end_to_end_latency_ms", "input_tokens", "output_tokens", "total_tokens", "model_requests", "domain_tool_calls", "coordination_tool_calls", "specialist_tool_invocations", "agent_invocations", "actual_agents"):
        result[key + "_total"] = sum(r[key] for r in rr) if all(r.get(key) is not None for r in rr) else None
        result[key + "_mean_per_attempt"] = statistics.mean(r[key] for r in rr) if rr and all(r.get(key) is not None for r in rr) else None
        result[key + "_median_of_case_medians"] = med([med([r.get(key) for r in rr if r["scenario_id"] == cid]) for cid in case_ids])
    return result


def figures(out, summaries, categories, failures, rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 11, "svg.fonttype": "none"})
    folder = out / "figures"
    folder.mkdir(exist_ok=True)
    def save(fig, name):
        fig.tight_layout()
        fig.savefig(folder / (name + ".svg"), bbox_inches="tight")
        fig.savefig(folder / (name + ".png"), dpi=220, bbox_inches="tight")
        plt.close(fig)
    def bars_with_unknown(ax, values, positions, **kwargs):
        for i, (position, value) in enumerate(zip(positions, values)):
            if value is None:
                ax.annotate("N/D", (position, 0), xytext=(0, 5), textcoords="offset points", ha="center")
            else:
                ax.bar(position, value, color=COLORS[i], **kwargs)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(LABELS, [r["observed_success_rate"] * 100 for r in summaries], color=COLORS)
    ax.set(ylabel="Sucessos observados / 200 (%)", ylim=(0, 100))
    save(fig, "01_sucesso")
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, key, label in zip(axes, ("end_to_end_latency_ms_median_of_case_medians", "estimated_generation_cost_usd", "estimated_cost_per_observed_task_success_usd"), ("Coletor: mediana de medianas (ms)", "Geração estimada (USD)", "Geração por sucesso observado (USD)")):
        bars_with_unknown(ax, [r[key] for r in summaries], range(3))
        ax.set_xticks(range(3), ("Supervisor", "Workflow", "Swarm"), rotation=15)
        ax.set_ylabel(label)
    save(fig, "02_latencia_custo_sucesso")
    names = sorted({r["category"] for r in categories})
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(names))
    for i, (arch, label, color) in enumerate(zip(ARCHES, LABELS, COLORS)):
        ax.bar(x + (i - 1) * .25, [next(r for r in categories if r["architecture"] == arch and r["category"] == n)["observed_success_rate"] * 100 for n in names], width=.25, color=color, label=label)
    ax.set_xticks(x, names, rotation=15)
    ax.set(ylabel="Sucessos observados / planejados (%)", ylim=(0, 100))
    ax.legend()
    save(fig, "03_categorias")
    fig, ax = plt.subplots(figsize=(8, 4))
    for i, r in enumerate(summaries):
        for offset, key, hatch in ((-.18, "pass_1_complete", None), (.18, "pass_5_complete", "//")):
            if r[key] is None:
                ax.annotate("N/D", (i + offset, 0), xytext=(0, 5), textcoords="offset points", ha="center")
            else:
                ax.bar(i + offset, r[key] * 100, width=.36, color=COLORS[i], hatch=hatch, alpha=.8)
    ax.set_xticks(range(3), LABELS)
    ax.set(ylabel="Consistência nos cenários completos (%)", ylim=(0, 100), title="Sem hachura: pass¹; hachura: pass⁵; denominadores na tabela")
    save(fig, "04_consistencia")
    classes = sorted({r["failure_class"] for r in failures})
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(classes))
    for i, (arch, label, color) in enumerate(zip(ARCHES, LABELS, COLORS)):
        ax.barh(x + (i - 1) * .25, [next(r["count"] for r in failures if r["architecture"] == arch and r["failure_class"] == n) for n in classes], height=.25, color=color, label=label)
    ax.set_yticks(x, classes)
    ax.set_xlabel("Unidades; classes principais exclusivas")
    ax.legend()
    save(fig, "05_falhas")


def table(rows, fields):
    def fmt(value):
        return "—" if value is None else f"{value:.4f}" if isinstance(value, float) else str(value)
    return "| " + " | ".join(fields) + " |\n| " + " | ".join("---" for _ in fields) + " |\n" + "".join("| " + " | ".join(fmt(r.get(k)) for k in fields) + " |\n" for r in rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--pilot", type=Path)
    p.add_argument("--connectivity", type=Path)
    p.add_argument("--integration", type=Path)
    args = p.parse_args()
    folder, out = args.folder.resolve(), args.output.resolve()
    manifest = read(folder / "manifest.json")
    rows = lines(folder / "aggregated-evaluations.jsonl")
    if manifest["configuration"]["protocol"] != "architectural-comparison-v4.2":
        raise ValueError("Only the corrected protocol may use this exporter")
    keys = [(r["scenario_id"], r["architecture"], r["repetition"]) for r in rows]
    expected = {(c["id"], arch, r) for c in manifest["cases"] for arch in ARCHES for r in range(5)}
    if len(rows) != 600 or len(set(keys)) != 600 or set(keys) != expected:
        raise ValueError("Require all 600 unique planned combinations; partial reports are forbidden")
    out.mkdir(parents=True, exist_ok=True)
    pricing = read(ROOT / "experiments/architectural-comparison-v42/pricing.json")
    rates = pricing["rates_per_million_tokens"]
    for row in rows:
        row["estimated_generation_cost_usd"] = priced(row.get("input_tokens"), row.get("output_tokens"), rates["haiku_4_5"])
        row["content_success"] = content_status(row)
        row["failure_class"] = failure_class(row)
    safe_fields = ["unit_id", "scenario_id", "architecture", "repetition", "stratum", "difficulty", "status", "success", "architectural_compliance", "task_success", "content_success", "procedure_applicable", "procedure_compliance", "failure_class", "latency_ms", "end_to_end_latency_ms", "input_tokens", "output_tokens", "total_tokens", "token_measurement_complete", "actual_agents", "agent_invocations", "model_requests", "domain_tool_calls", "coordination_tool_calls", "specialist_tool_invocations", "handoffs_requested", "inter_agent_explicit_messages", "estimated_generation_cost_usd"]
    safe = [{k: r.get(k) for k in safe_fields} for r in rows]
    csvwrite(out / "units.csv", safe)
    (out / "units.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in safe))
    summaries = [summary(a, rows) for a in ARCHES]
    categories = [summary(a, rows, category=c) for c in sorted({r["stratum"] for r in rows}) for a in ARCHES]
    difficulties = [summary(a, rows, difficulty=d) for d in sorted({r["difficulty"] for r in rows}) for a in ARCHES]
    csvwrite(out / "architecture-summary.csv", summaries)
    csvwrite(out / "category-summary.csv", categories)
    csvwrite(out / "difficulty-summary.csv", difficulties)
    ids = sorted({r["scenario_id"] for r in rows})
    scenario = []
    for cid in ids:
        for arch in ARCHES:
            rr = [r for r in rows if r["scenario_id"] == cid and r["architecture"] == arch]
            scenario.append({"scenario_id": cid, "architecture": arch, "planned": 5, "task_successes": sum(r["task_success"] is True for r in rr), "task_unknown": sum(r["task_success"] is None for r in rr), **{k + "_median": med([r.get(k) for r in rr]) for k in ("latency_ms", "end_to_end_latency_ms", "total_tokens", "estimated_generation_cost_usd")}})
    csvwrite(out / "scenario-metrics.csv", scenario)
    distributions = []
    secondary_pairs = []
    for key in ("latency_ms", "end_to_end_latency_ms", "total_tokens", "estimated_generation_cost_usd"):
        for arch in ARCHES:
            for phase in ("technical_completed", "technical_failure"):
                values = [r[key] for r in rows if r["architecture"] == arch and r.get(key) is not None and bool(r.get("success")) == (phase == "technical_completed")]
                distributions.append({"architecture": arch, "metric": key, "status_group": phase, "measured_n": len(values), "planned": 200,
                                      **{name: float(np.quantile(values, q)) if values else None for name, q in (("min", 0), ("q25", .25), ("median", .5), ("q75", .75), ("p95", .95), ("max", 1))}})
        for a, b in itertools.combinations(ARCHES, 2):
            pairs = [(next(r for r in scenario if r["scenario_id"] == cid and r["architecture"] == a)[key + "_median"], next(r for r in scenario if r["scenario_id"] == cid and r["architecture"] == b)[key + "_median"]) for cid in ids]
            known = [(a_value, b_value) for a_value, b_value in pairs if a_value is not None and b_value is not None]
            secondary_pairs.append({"architecture_a": a, "architecture_b": b, "metric": key, "paired_scenarios": len(known), "excluded_scenarios": len(ids) - len(known), "median_paired_difference_b_minus_a": med([bv - av for av, bv in known]), "median_paired_ratio_b_over_a": med([bv / av for av, bv in known if av])})
    csvwrite(out / "measurement-distributions.csv", distributions)
    csvwrite(out / "paired-secondary-effects.csv", secondary_pairs)
    paired = []
    for a, b in itertools.combinations(ARCHES, 2):
        differences = [(next(r for r in scenario if r["scenario_id"] == cid and r["architecture"] == b)["task_successes"] - next(r for r in scenario if r["scenario_id"] == cid and r["architecture"] == a)["task_successes"]) / 5 for cid in ids]
        paired.append({"architecture_a": a, "architecture_b": b, **paired_success(differences)})
    for row, adjusted in zip(paired, holm([r["p_unadjusted"] for r in paired])):
        row["p_holm_three_comparisons"] = adjusted
    csvwrite(out / "paired-success.csv", paired)
    failure_names = sorted({r["failure_class"] for r in rows if r["failure_class"] != "success"})
    failures = [{"architecture": a, "failure_class": f, "count": sum(r["architecture"] == a and r["failure_class"] == f for r in rows), "denominator": 200} for f in failure_names for a in ARCHES]
    assert sum(r["count"] for r in failures) == sum(r["task_success"] is not True for r in rows)
    csvwrite(out / "failure-classes.csv", failures)
    quality = [{"architecture": a, "dimension": d, "score": score, "count": sum(r["architecture"] == a and r.get("evaluation") is not None and r["evaluation"]["quality"][d] == score for r in rows), "planned": 200} for a in ARCHES for d in DIMS for score in (*range(1, 6), None)]
    for a in ARCHES:
        for d in DIMS:
            next(r for r in quality if r["architecture"] == a and r["dimension"] == d and r["score"] is None)["count"] += sum(r["architecture"] == a and r.get("evaluation") is None for r in rows)
    csvwrite(out / "quality-distributions.csv", quality)
    critical = [{"architecture": a, "source": source, "violation": v, "flagged": sum(r["architecture"] == a and any(x["violation_id"] == v for x in (r.get(source) or {}).get("critical_violations", [])) for r in rows), "overlapping": True, "planned": 200} for a in ARCHES for source in ("evaluation", "objective_checks") for v in ("V1", "V2", "V3", "V4")]
    csvwrite(out / "critical-flags.csv", critical)
    resources = {"generation": generation_resources(folder, rates["haiku_4_5"]), "judgment": judgments_resources(folder, "primary", rates["sonnet_4_5"]), "recheck": judgments_resources(folder, "recheck", rates["sonnet_4_5"]), "pricing": pricing}
    if args.pilot:
        resources["engineering_pilot"] = generation_resources(args.pilot, rates["haiku_4_5"])
        resources["engineering_pilot_judgment"] = judgments_resources(args.pilot, "primary", rates["sonnet_4_5"])
    if args.connectivity:
        checks = lines(args.connectivity / "connectivity.jsonl")
        resources["connectivity"] = [{"model_id": r["model_id"], "usage": r.get("usage"), "estimated_cost_usd": priced((r.get("usage") or {}).get("inputTokens"), (r.get("usage") or {}).get("outputTokens"), rates["haiku_4_5" if "haiku" in r["model_id"] else "sonnet_4_5"])} for r in checks]
    if args.integration:
        resources["api_integration"] = generation_resources(args.integration, rates["haiku_4_5"])
    dump(out / "resource-consumption.json", resources)
    generation = resources["generation"]
    if generation["usage_complete"]:
        for key, label in (("inputTokens", "input_tokens"), ("outputTokens", "output_tokens"), ("totalTokens", "total_tokens")):
            assert generation["known_" + key] == sum(r[label] for r in rows), "Physical usage did not reconcile"
    old = list(csv.DictReader((ROOT / "research-data/results/matrix40-v1-final/architecture-summary.csv").open()))
    history = [{"cohort": "v4.1 historical", "architecture": r["architecture"], "implementation": "single agent with domain tools" if r["architecture"] == ARCHES[0] else r["architecture"], "planned": 200, "task_successes": int(r["task_successes"]), "task_unknown": int(r["task_unknown"])} for r in old]
    history += [{"cohort": "v4.2 new", "architecture": r["architecture"], "implementation": "supervisor with specialists as tools" if r["architecture"] == ARCHES[0] else r["architecture"], "planned": 200, "task_successes": r["task_successes"], "task_unknown": r["task_unknown"]} for r in summaries]
    csvwrite(out / "historical-comparison.csv", history)
    recheck = read(folder / "recheck-analysis.json")
    provenance = {"protocol": manifest["configuration"]["protocol"], "experiment_id": manifest["experiment_id"], "commit": manifest["commit"], "manifest_sha256": sha(folder / "manifest.json"), "cases_sha256": manifest["cases_sha256"], "dependencies": manifest["dependency_versions"], "configuration": manifest["configuration"], "analysis_plan": manifest.get("analysis_plan"), "source_sha256": sha(Path(__file__)), "exported_at": datetime.now(timezone.utc).isoformat(), "units": 600, "unique_combinations": len(set(keys)), "human_review_performed": False, "raw_conversations_published": False}
    dump(out / "provenance.json", provenance)
    dump(out / "recheck-analysis.json", recheck)
    dump(out / "results-summary.json", {"generated": 600, "judgment_attempted_responses": len({r["response_id"] for r in lines(folder / "judge-attempts.jsonl") if r["phase"] == "primary"}), "valid_judgments": sum(r.get("evaluation") is not None for r in rows), "architectures": summaries, "paired_success": paired})
    figures(out, summaries, categories, failures, rows)
    report = "# Nova comparação arquitetural — v4.2\n\n"
    report += "Foram preservadas 600 unidades novas e únicas: 40 cenários × cinco repetições × três arquiteturas. A condição centralizada usa supervisor com agentes especialistas como ferramentas. O cenário é a unidade pareada; as cinco repetições permanecem agrupadas.\n\n"
    report += table(summaries, ["architecture", "planned", "technical_successes", "architectural_compliant", "architectural_violations", "task_successes", "task_failures", "task_unknown", "judge_schema_valid", "judge_valid_assessment"])
    report += "\nO sucesso exige conclusão técnica, conformidade arquitetural, conteúdo sob o instrumento congelado e consulta obrigatória comprovada. Julgamentos inválidos e desconhecidos são explícitos. Falhas legítimas foram preservadas; a seleção não depende de favorecer uma arquitetura.\n\n"
    report += table(paired, ["architecture_a", "architecture_b", "paired_scenarios", "difference_pp_b_minus_a", "bootstrap_95_low_pp", "bootstrap_95_high_pp", "p_holm_three_comparisons"])
    report += "\nIntervalos percentis usam 20.000 reamostragens de cenários. Testes bilaterais de permutação pareada usam enumeração exata até 16 diferenças não nulas ou 99.999 permutações, com ajuste plus-one; Holm corrige as três comparações. Semente 20261011. Intervalos são condicionais à amostra intencional conhecida; não demonstram generalização clínica.\n\n"
    report += table(summaries, ["architecture", "content_successes", "content_evaluable", "mandatory_evidence_applicable", "mandatory_evidence_compliant", "mandatory_evidence_evaluable", "complete_scenarios", "pass_1_complete", "pass_5_complete"])
    report += "\nLatência do núcleo (`latency_ms`), latência do coletor (`end_to_end_latency_ms`, processo/importações/arquivos), API e julgamento têm fronteiras distintas. O benchmark mede o transporte histórico direto do núcleo, sem HTTP, banco ou interface. Os contadores somam requisições físicas únicas; métricas acumuladas dos agentes não são somadas novamente.\n\n"
    report += table(summaries, ["architecture", "end_to_end_latency_ms_median_of_case_medians", "total_tokens_total", "model_requests_total", "domain_tool_calls_total", "specialist_tool_invocations_total", "estimated_generation_cost_usd", "estimated_cost_per_observed_task_success_usd"])
    report += "\nCustos em USD são estimativas de tokens observados com tarifas públicas de 02/11/2026, região us-west-2 e perfil geográfico US. Geração, julgamento, rechecagem, conectividade, piloto e integração estão separados em resource-consumption.json. Não são cobrança efetiva. Tokens desconhecidos permanecem desconhecidos.\n\n"
    report += table(failures, ["architecture", "failure_class", "count", "denominator"])
    report += "\nAs classes principais são exclusivas e recuperam todas as unidades sem sucesso observado, incluindo desconhecidos. Marcações críticas em critical-flags.csv são indicadores sobrepostos. Trajetórias e exemplos com entradas/retornos completos ficam no pacote privado; eventos demonstram consulta e circulação de resultados, sem inferir raciocínio interno.\n\n"
    report += "## Histórico separado\n\n" + table(history, ["cohort", "architecture", "implementation", "planned", "task_successes", "task_unknown"])
    report += "\nOs lotes não foram agrupados. A comparação histórica não identifica efeito causal da correção. O lote antigo central mede agente único. A nova coleta pode melhorar ou piorar; o objetivo é avaliar a implementação correta.\n\n"
    report += "## Rechecagem e limites\n\n" + f"Rechecagem do mesmo juiz: {recheck.get('evaluated')}/15; mudanças de classificação: {recheck.get('success_classification_changes')}. O julgamento principal foi preservado. Nenhuma revisão farmacêutica ou avaliação humana foi realizada.\n\n"
    report += "Fontes e gabaritos são técnicos e controlados; anexos oferecem metadados. A amostragem é intencional, os casos são conhecidos e não constituem teste externo independente. Não há validação clínica. Relatórios anteriores, TCC e Report 6 não foram sobrescritos.\n\n"
    for stem in ("01_sucesso", "02_latencia_custo_sucesso", "03_categorias", "04_consistencia", "05_falhas"):
        report += f"![{stem}](figures/{stem}.png)\n\n"
    report += "Inventário: units.csv/jsonl (600 combinações), scenario-metrics.csv (120 grupos), resumos por arquitetura/categoria/dificuldade, paired-success.csv, quality-distributions.csv, critical-flags.csv, failure-classes.csv, historical-comparison.csv, resource-consumption.json, provenance.json e figuras SVG/PNG. O pacote privado contém manifestos, snapshots, respostas, eventos, gabaritos, avaliações e comandos.\n"
    (out / "RELATORIO.md").write_text(report)
    (out / "README.md").write_text("# Resultados sanitizados v4.2\n\nLeia RELATORIO.md e provenance.json. Mensagens, trajetórias e gabaritos integrais permanecem no pacote restrito.\n")
    dump(out / "FILES.json", {str(f.relative_to(out)): {"sha256": sha(f), "bytes": f.stat().st_size} for f in sorted(out.rglob("*")) if f.is_file() and f.name != "FILES.json"})
    print(json.dumps({"units": 600, "successes": sum(r["task_success"] is True for r in rows), "output": str(out)}))


if __name__ == "__main__":
    main()
