"""YAML scenario loader for E2E quality tests and benchmarks."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Iterable

import yaml


def load_yaml_scenarios(
    scenarios_dir: Path,
    *,
    selected_ids: Iterable[str] | None = None,
    architectures_override: Iterable[str] | None = None,
) -> list[tuple[str, dict, str]]:
    """Load YAML scenario suites and expand per architecture.

    Returns a list of (test_id, case_dict, architecture) tuples where test_id is
    ``{suite}-{case_id}-{architecture}``. Applies per-case architectures (if present)
    otherwise suite defaults, unless *architectures_override* is provided (which wins).
    If *selected_ids* is provided, only cases whose ``id`` is in the set are kept.
    Each returned case is a deep copy so callers can mutate it safely.
    """
    id_filter: set[str] | None = set(selected_ids) if selected_ids is not None else None
    arch_list: list[str] | None = list(architectures_override) if architectures_override is not None else None

    items: list[tuple[str, dict, str]] = []

    for path in sorted(scenarios_dir.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text())

        suite = doc.get("suite")
        assert suite, f"{path.name}: missing 'suite'"
        cases = doc.get("cases")
        if not cases:
            continue

        defaults = doc.get("defaults", {})
        default_archs = defaults.get("architectures", ["centralized_orchestration"])
        default_timeout = defaults.get("timeout_seconds", 30)

        for case in cases:
            assert case.get("id"), f"{path.name}: case missing 'id'"
            assert case.get("input", {}).get("text"), f"{path.name}: case {case.get('id')}: missing 'input.text'"
            assert case.get("expected", {}).get("route"), f"{path.name}: case {case.get('id')}: missing 'expected.route'"

            if id_filter is not None and case["id"] not in id_filter:
                continue

            case.setdefault("timeout_seconds", default_timeout)
            per_case_archs = case.pop("architectures", None) or default_archs
            archs = arch_list if arch_list is not None else per_case_archs

            for arch in archs:
                test_id = f"{suite}-{case['id']}-{arch}"
                items.append((test_id, copy.deepcopy(case), arch))

    return items
