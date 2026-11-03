#!/usr/bin/env python3
"""Release a frozen v4.4 cohort only after the separate technical pilot."""
import argparse
import ast
from collections import Counter, defaultdict
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path


ARCHITECTURES = ("centralized_orchestration", "structured_workflow", "decentralized_swarm")
COMPARISON = Path("apps/agent-runtime/app/architectures/comparison.py")
DOMAIN_TOOLS = (
    "apps/agent-runtime/app/tools/domain_tools.py",
    "apps/agent-runtime/app/tools/research_tools.py",
)


def read(path):
    return json.loads(path.read_text())


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def frozen_comparators(path):
    module = ast.parse(path.read_text())
    definition = next(node for node in module.body if isinstance(node, ast.FunctionDef)
                      and node.name == "execute_comparison")
    central = next(node for node in definition.body if isinstance(node, ast.If)
                   and isinstance(node.test, ast.Compare)
                   and isinstance(node.test.comparators[0], ast.Constant)
                   and node.test.comparators[0].value == ARCHITECTURES[0])
    return ast.dump(central.orelse[0], include_attributes=False)


def logical_order(manifest):
    return [tuple(unit[key] for key in ("scenario_id", "architecture", "repetition", "block", "position"))
            for unit in manifest["order"]]


def release(pilot, main, historical_manifest):
    pilot_manifest = pilot / "manifest.json"
    main_manifest = main / "manifest.json"
    pilot_plan, main_plan, historical = map(read, (pilot_manifest, main_manifest, historical_manifest))
    if any(list(main.glob(pattern)) for pattern in ("*/launch.json", "*/started.json", "*/result.json")):
        raise ValueError("Main collection already started")
    cases = main_plan["cases"]
    pilot_cases = pilot_plan["cases"]
    historical_config = historical["configuration"]
    evaluation = main_plan["evaluation_plan"]
    metric_keys = ("model_id", "temperature", "max_tokens", "version", "objective_check_version",
                   "configuration_sha256")
    settings_match = main_plan["settings"] == historical["settings"] == pilot_plan["settings"]
    dependencies_match = (main_plan["dependency_versions"] == historical["dependency_versions"]
                          == pilot_plan["dependency_versions"])
    judge_matches = all(evaluation[key] == historical["evaluation_plan"][key] == pilot_plan["evaluation_plan"][key]
                        for key in metric_keys)
    assets_match = main_plan["asset_hashes"] == historical["asset_hashes"] and all(
        digest(main / "assets-snapshot" / name) == expected for name, expected in main_plan["asset_hashes"].items()
    )
    comparator_match = frozen_comparators(main / "code-snapshot" / COMPARISON) == frozen_comparators(
        historical_manifest.parent / "code-snapshot" / COMPARISON
    )
    sources_match = all(main_plan["code_hashes"][name] == historical["code_hashes"][name] for name in DOMAIN_TOOLS)
    config_match = all(main_plan["configuration"][key] == historical_config[key]
                       for key in ("domain_policy", "role_prompts", "tool_schema_hashes", "referral_policy"))
    counts = Counter(unit["architecture"] for unit in main_plan["order"])
    unique_combinations = {(unit["scenario_id"], unit["architecture"], unit["repetition"])
                           for unit in main_plan["order"]}
    expected_combinations = {(case["id"], arch, repetition) for case in cases
                             for arch in ARCHITECTURES for repetition in range(5)}
    plans_ok = (
        main_plan["configuration"]["protocol"] == pilot_plan["configuration"]["protocol"]
        == "architectural-comparison-v4.4"
        and main_plan["analysis_plan_sha256"] == pilot_plan["analysis_plan_sha256"]
        and main_plan["configuration"] == pilot_plan["configuration"]
        and main_plan["code_hashes"] == pilot_plan["code_hashes"]
        and main_plan["generation_dispatch"] == pilot_plan["generation_dispatch"]
        and 1 <= evaluation["dispatch_workers"] <= 48
        and len(main_plan["order"]) == len(unique_combinations) == 600
        and unique_combinations == expected_combinations
        and len(main_plan["stability_recheck_plan"]["unit_ids"]) == 15
    )

    pilot_runs = lines(pilot / "runs.jsonl")
    expected_units = [unit["unit_id"] for unit in pilot_plan["order"]]
    contexts = defaultdict(set)
    provider_ids = set()
    provider_integrity = True
    final_authority = True
    rejected_requests = 0
    expected_final_roles = dict(zip(ARCHITECTURES, ("supervisor", "synthesizer", "synthesizer"), strict=True))
    for run in pilot_runs:
        events = lines(pilot / run["unit_id"] / "events.jsonl")
        first_agent = next((e for e in events if e["eventFamily"] == "agent" and e["eventName"] == "started"), None)
        contexts[run["scenario_id"]].add(first_agent["payload"].get("inputSha256") if first_agent else None)
        starts = [e["payload"]["callId"] for e in events if e["eventFamily"] == "model" and e["eventName"] == "started"]
        completed = {e["payload"]["callId"]: e["payload"].get("usage") for e in events
                     if e["eventFamily"] == "model" and e["eventName"] == "completed"}
        if (set(starts) != completed.keys() or provider_ids.intersection(starts)
                or len(starts) != len(set(starts)) or len(starts) != run["model_requests"]
                or not all(completed.values())
                or sum(v["totalTokens"] for v in completed.values()) != run["total_tokens"]):
            provider_integrity = False
        provider_ids.update(starts)
        final_events = [e for e in events if (e["eventFamily"], e["eventName"]) == ("response", "final")]
        final_authority &= (len(final_events) == 1
                            and final_events[0].get("actorName") == expected_final_roles[run["architecture"]])
        rejected_requests += sum((e["eventFamily"], e["eventName"]) == ("tool", "rejected") for e in events)

    checks = {
        "historical_cases_exact": len(cases) == 40 and cases == historical["cases"]
                                  and main_plan["cases_sha256"] == historical["cases_sha256"],
        "historical_assets_exact": assets_match,
        "historical_comparator_bodies_exact": comparator_match,
        "historical_source_files_exact": sources_match,
        "historical_domain_and_role_configuration_exact": config_match,
        "historical_logical_order_exact": logical_order(main_plan) == logical_order(historical),
        "generation_settings_exact": settings_match,
        "dependency_versions_exact": dependencies_match,
        "judge_instrument_exact": judge_matches,
        "plans_frozen_and_compatible": plans_ok,
        "pilot_is_separate_synthetic": len(pilot_cases) == 6
                                      and all(c["origin"] == "synthetic-authored" for c in pilot_cases),
        "pilot_all_units": len(pilot_runs) == 18 and [r["unit_id"] for r in pilot_runs] == expected_units,
        "pilot_all_technical_success": len(pilot_runs) == 18 and all(r["success"] for r in pilot_runs),
        "pilot_all_contracts_pass": len(pilot_runs) == 18 and all(r["architectural_compliance"] is True for r in pilot_runs),
        "pilot_all_usage_measured": len(pilot_runs) == 18 and all(r["token_measurement_complete"] for r in pilot_runs),
        "pilot_inputs_match_within_scenario": len(contexts) == 6
                                            and all(len(values) == 1 and None not in values for values in contexts.values()),
        "pilot_provider_ids_and_tokens_reconciled": provider_integrity,
        "pilot_final_authority_verified": final_authority,
    }
    result = {
        "protocol": "architectural-comparison-v4.4",
        "released_at_utc": datetime.now(UTC).isoformat(),
        "passed": all(checks.values()),
        "checks": checks,
        "main_manifest_sha256": digest(main_manifest),
        "pilot_manifest_sha256": digest(pilot_manifest),
        "historical_manifest_sha256": digest(historical_manifest),
        "planned_by_architecture": dict(counts),
        "pilot_attempts": len(pilot_runs),
        "pilot_technical_successes": sum(r["success"] for r in pilot_runs),
        "pilot_architectural_conformant": sum(r["architectural_compliance"] is True for r in pilot_runs),
        "pilot_provider_requests": len(provider_ids),
        "pilot_scope_rejected_tool_requests": rejected_requests,
        "generation_workers": main_plan["generation_dispatch"]["workers"],
        "judge_workers": evaluation["dispatch_workers"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    if result["passed"]:
        with (main / "engineering-gate.json").open("x") as output:
            json.dump(result, output, ensure_ascii=False, indent=2)
            output.write("\n")
    return result["passed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--main", type=Path, required=True)
    parser.add_argument("--historical-manifest", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if release(args.pilot, args.main, args.historical_manifest) else 1)
