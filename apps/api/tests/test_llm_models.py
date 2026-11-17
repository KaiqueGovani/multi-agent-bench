"""Model discovery proxies use credentials without storing or reflecting them."""
from io import BytesIO
import json
from urllib.error import HTTPError, URLError

import pytest

from tests.test_bedrock_settings import settings_api


def discover(client, body):
    return client.post("/settings/llm/models", json=body, headers={"X-API-Key": "settings-test-key"})


def test_discovery_requires_authentication(settings_api, monkeypatch):
    def no_forward(*args, **kwargs):
        pytest.fail("Unauthenticated discovery must not reach the runtime")
    monkeypatch.setattr("app.api.routes.settings.urlopen", no_forward)
    response = settings_api.post("/settings/llm/models", json={"provider": "anthropic", "apiKey": "private-credential"})
    assert response.status_code == 401
    assert "private-credential" not in response.text


@pytest.mark.parametrize(("provider", "source"), [("anthropic", "provider"), ("bedrock", "catalog")])
@pytest.mark.parametrize(("key", "forwarded_key"), [(None, None), ("", None), ("  ", None), ("  private-credential  ", "private-credential")])
def test_discovery_forwards_optional_key_without_mutating_settings(settings_api, monkeypatch, caplog, provider, source, key, forwarded_key):
    calls = []
    listing = {"provider": provider, "models": [{"id": "claude-haiku-4-5", "name": "Claude Haiku 4.5"}], "source": source}
    def runtime(request, timeout):
        calls.append(request)
        return BytesIO(json.dumps({
            **listing, "apiKey": "private-credential",
            "models": [{**listing["models"][0], "apiKey": "private-credential"}],
        }).encode())
    monkeypatch.setattr("app.api.routes.settings.urlopen", runtime)
    body = {"provider": provider, "modelId": "not-forwarded", "unknown": "private-credential"}
    if key is not None:
        body["apiKey"] = key
    response = discover(settings_api, body)
    assert response.status_code == 200
    assert response.json() == listing
    assert response.headers["cache-control"] == "no-store"
    assert len(calls) == 1
    assert calls[0].method == "POST"
    assert calls[0].full_url == "http://runtime.test:8010/settings/llm/models"
    assert calls[0].get_header("X-ai-service-secret") == "runtime-shared-secret"
    forwarded = {"provider": provider}
    if forwarded_key:
        forwarded["apiKey"] = forwarded_key
    assert json.loads(calls[0].data) == forwarded
    assert "private-credential" not in response.text
    assert "private-credential" not in caplog.text


@pytest.mark.parametrize("payload", [
    None, [], {}, {"provider": []}, {"provider": {}}, {"provider": "unknown"},
    {"provider": "anthropic", "apiKey": []}, {"provider": "anthropic", "apiKey": 123},
    {"provider": "anthropic", "apiKey": "private credential"},
    {"provider": "anthropic", "apiKey": "private\u200bcredential"},
])
def test_invalid_discovery_payload_is_sanitized(settings_api, monkeypatch, payload):
    def no_forward(*args, **kwargs):
        pytest.fail("Invalid discovery requests must not reach the runtime")
    monkeypatch.setattr("app.api.routes.settings.urlopen", no_forward)
    response = discover(settings_api, payload)
    assert response.status_code == 400
    assert "private" not in response.text


@pytest.mark.parametrize(("failure", "expected", "message"), [
    (URLError("private-credential"), 503, "unavailable"),
    (HTTPError("http://runtime.test", 400, "private-credential", {}, BytesIO(b"private-credential")), 400, "API key"),
    (HTTPError("http://runtime.test", 403, "private-credential", {}, BytesIO(b"private-credential")), 503, "AI_SERVICE_SECRET"),
    (HTTPError("http://runtime.test", 429, "private-credential", {}, BytesIO(b"private-credential")), 503, "rate limited"),
    (HTTPError("http://runtime.test", 502, "private-credential", {}, BytesIO(b"private-credential")), 502, "API key"),
    (HTTPError("http://runtime.test", 504, "private-credential", {}, BytesIO(b"private-credential")), 504, "timed out"),
])
def test_discovery_errors_are_readable_without_credential_disclosure(settings_api, monkeypatch, caplog, failure, expected, message):
    def fail(*args, **kwargs):
        raise failure
    monkeypatch.setattr("app.api.routes.settings.urlopen", fail)
    response = discover(settings_api, {"provider": "anthropic", "apiKey": "private-credential"})
    assert response.status_code == expected
    assert message in response.text
    assert "private-credential" not in response.text
    assert "private-credential" not in caplog.text


@pytest.mark.parametrize("listing", [
    {}, [], {"provider": "unknown", "models": [], "source": "provider"},
    {"provider": "bedrock", "models": [], "source": "provider"},
    {"provider": "anthropic", "models": [], "source": "private-credential"},
    {"provider": "anthropic", "models": [{"id": "", "name": "Name"}], "source": "provider"},
    {"provider": "anthropic", "models": [{"id": "private credential", "name": "Name"}], "source": "provider"},
    {"provider": "anthropic", "models": [{"id": "claude", "name": "private\ncredential"}], "source": "provider"},
    {"provider": "anthropic", "models": [{"id": "claude"}], "source": "provider"},
])
def test_invalid_runtime_model_listing_is_sanitized(settings_api, monkeypatch, listing):
    monkeypatch.setattr("app.api.routes.settings.urlopen", lambda *args, **kwargs: BytesIO(json.dumps(listing).encode()))
    response = discover(settings_api, {"provider": "anthropic", "apiKey": "private-credential"})
    assert response.status_code == 502
    assert response.json() == {"detail": "The runtime returned an invalid model list."}
    assert "private-credential" not in response.text
