from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _force_mock_llm(monkeypatch):
    """Unit tests must be deterministic: never call Bedrock.

    Forces ENABLE_LIVE_LLM=false regardless of the developer's .env, and
    clears the Settings lru_cache so the change takes effect.
    """
    monkeypatch.setenv("ENABLE_LIVE_LLM", "false")
    from app.core import config as _config
    _config.get_settings.cache_clear()
    yield
    _config.get_settings.cache_clear()
