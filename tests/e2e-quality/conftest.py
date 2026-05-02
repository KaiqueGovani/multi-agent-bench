"""Fixtures and parametrization for E2E quality tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from api_client import E2EClient
from _loader import load_yaml_scenarios

SCENARIOS_DIR = Path(__file__).parent / "scenarios"


# -- fixtures -------------------------------------------------------------

@pytest.fixture(scope="session")
def api_client():
    base_url = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
    api_key = os.environ.get("API_KEY", "poc-dev-key-2026")
    with E2EClient(base_url, api_key) as client:
        yield client


# -- parametrization ------------------------------------------------------

def pytest_generate_tests(metafunc):
    if "case" in metafunc.fixturenames and "architecture" in metafunc.fixturenames:
        scenarios = load_yaml_scenarios(SCENARIOS_DIR)
        ids = [s[0] for s in scenarios]
        argvalues = [(s[1], s[2]) for s in scenarios]
        metafunc.parametrize("case,architecture", argvalues, ids=ids)
