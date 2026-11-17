"""Fixtures and parametrization for E2E quality tests."""

from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

from api_client import E2EClient
from _loader import load_yaml_scenarios

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from local_api_key import configured_api_key

SCENARIOS_DIR = Path(__file__).parent / "scenarios"


# -- fixtures -------------------------------------------------------------

@pytest.fixture(scope="session")
def api_client():
    base_url = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
    try:
        api_key = configured_api_key(ROOT, os.environ.get("API_KEY"))
    except ValueError as error:
        pytest.fail(str(error), pytrace=False)
    with E2EClient(base_url, api_key) as client:
        yield client


# -- parametrization ------------------------------------------------------

def pytest_generate_tests(metafunc):
    if "case" in metafunc.fixturenames and "architecture" in metafunc.fixturenames:
        scenarios = load_yaml_scenarios(SCENARIOS_DIR)
        ids = [s[0] for s in scenarios]
        argvalues = [(s[1], s[2]) for s in scenarios]
        metafunc.parametrize("case,architecture", argvalues, ids=ids)
