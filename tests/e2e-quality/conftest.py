"""Fixtures and parametrization for E2E quality tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from api_client import E2EClient

SCENARIOS_DIR = Path(__file__).parent / "scenarios"


# -- fixtures -------------------------------------------------------------

@pytest.fixture(scope="session")
def api_client():
    base_url = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
    api_key = os.environ.get("API_KEY", "poc-dev-key-2026")
    with E2EClient(base_url, api_key) as client:
        yield client


# -- parametrization ------------------------------------------------------

def _load_scenarios() -> list[tuple[str, dict, str]]:
    """Return list of (test_id, case_dict, architecture) tuples."""
    items: list[tuple[str, dict, str]] = []

    for path in sorted(SCENARIOS_DIR.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text())

        # Validate required fields
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

            # Apply defaults
            case.setdefault("timeout_seconds", default_timeout)
            archs = case.pop("architectures", None) or default_archs

            for arch in archs:
                test_id = f"{suite}-{case['id']}-{arch}"
                items.append((test_id, case, arch))

    return items


def pytest_generate_tests(metafunc):
    if "case" in metafunc.fixturenames and "architecture" in metafunc.fixturenames:
        scenarios = _load_scenarios()
        ids = [s[0] for s in scenarios]
        argvalues = [(s[1], s[2]) for s in scenarios]
        metafunc.parametrize("case,architecture", argvalues, ids=ids)
