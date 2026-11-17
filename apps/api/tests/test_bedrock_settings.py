"""Rotate provider credentials through the protected API without contacting AWS."""
from io import BytesIO
import json
from urllib.error import HTTPError, URLError

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
def settings_api(monkeypatch):
    monkeypatch.setenv("API_KEY", "settings-test-key")
    monkeypatch.setenv("AI_RUNTIME_URL", "http://runtime.test:8010/")
    monkeypatch.setenv("AI_SERVICE_SECRET", "runtime-shared-secret")
    # Per-message real mode remains available with a globally mocked API.
    monkeypatch.setenv("RUNTIME_MODE", "mock")
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()


def update(client, body):
    return client.put("/settings/bedrock", json=body, headers={"X-API-Key": "settings-test-key"})


def status_payload(**overrides):
    return {
        "enabled": True,
        "tokenConfigured": True,
        "sdkAvailable": True,
        "ready": True,
        "modelId": "test-bedrock-model",
        "region": "us-east-1",
        "provider": "bedrock",
        "models": {"bedrock": "test-bedrock-model", "anthropic": "claude-haiku-4-5"},
        "credentialsConfigured": {"bedrock": True, "anthropic": False},
        **overrides,
    }


def test_requires_api_auth_before_forwarding(settings_api, monkeypatch):
    def no_forward(*args, **kwargs):
        pytest.fail("Unauthenticated requests must not reach the runtime")
    monkeypatch.setattr("app.api.routes.settings.urlopen", no_forward)
    response = settings_api.put("/settings/bedrock", json={"apiKey": "secret-test-token"})
    assert response.status_code == 401
    assert "secret-test-token" not in response.text


def test_forwards_trimmed_key_with_shared_secret_and_returns_only_status(settings_api, monkeypatch, caplog):
    key = "bedrock-api-key-test-rotation"
    calls = []

    def runtime(request, timeout):
        calls.append((request, timeout))
        return BytesIO(json.dumps(status_payload(apiKey=key, unexpectedCredential=key)).encode())

    monkeypatch.setattr("app.api.routes.settings.urlopen", runtime)
    response = update(settings_api, {"apiKey": f"  {key}\n"})
    assert response.status_code == 200, response.text
    forwarded, timeout = calls[0]
    assert forwarded.full_url == "http://runtime.test:8010/settings/bedrock"
    assert forwarded.method == "PUT"
    assert forwarded.get_header("X-ai-service-secret") == "runtime-shared-secret"
    assert json.loads(forwarded.data) == {"apiKey": key}
    assert timeout == get_settings().ai_runtime_timeout_seconds
    assert response.json() == {
        "mode": "mock", "runtimeUrl": "http://runtime.test:8010/", "reachable": True,
        "ready": True, "llm": status_payload(), "error": None,
    }
    assert response.headers["cache-control"] == "no-store"
    assert key not in response.text
    assert key not in caplog.text


@pytest.mark.parametrize("body", [None, [], {}, {"apiKey": None}, {"apiKey": 123}, {"apiKey": " "},
                                      {"apiKey": "secret token"}, {"apiKey": "secret\u0000token"},
                                      {"apiKey": "secret\u007ftoken"}, {"apiKey": "secret\u0085token"},
                                      {"apiKey": "secret\u200btoken"}, {"apiKey": "x" * 16385}])
def test_invalid_keys_never_reach_runtime_or_echo_input(settings_api, monkeypatch, body):
    def no_forward(*args, **kwargs):
        pytest.fail("Invalid keys must not reach the runtime")
    monkeypatch.setattr("app.api.routes.settings.urlopen", no_forward)
    response = update(settings_api, body)
    assert response.status_code == 400
    assert "secret" not in response.text
    assert "input" not in response.text


def test_malformed_json_does_not_echo_input(settings_api):
    response = settings_api.put(
        "/settings/bedrock", content='{"apiKey":"private-credential"',
        headers={"X-API-Key": "settings-test-key", "Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert "private-credential" not in response.text


def test_missing_runtime_configuration_is_actionable(settings_api, monkeypatch):
    monkeypatch.delenv("AI_RUNTIME_URL")
    get_settings.cache_clear()
    response = update(settings_api, {"apiKey": "private-credential"})
    assert response.status_code == 503
    assert "AI_RUNTIME_URL" in response.text
    assert "private-credential" not in response.text


@pytest.mark.parametrize("failure,expected", [
    (URLError("private-credential"), 503),
    (TimeoutError("private-credential"), 503),
    (HTTPError("http://runtime.test", 403, "private-credential", {}, BytesIO(b"private-credential")), 503),
    (HTTPError("http://runtime.test", 400, "private-credential", {}, BytesIO(b"private-credential")), 400),
    (HTTPError("http://runtime.test", 500, "private-credential", {}, BytesIO(b"private-credential")), 502),
])
def test_upstream_failures_are_sanitized(settings_api, monkeypatch, caplog, failure, expected):
    def fail(*args, **kwargs):
        raise failure
    monkeypatch.setattr("app.api.routes.settings.urlopen", fail)
    response = update(settings_api, {"apiKey": "private-credential"})
    assert response.status_code == expected
    assert "private-credential" not in response.text
    assert "private-credential" not in caplog.text


def test_invalid_runtime_status_is_sanitized(settings_api, monkeypatch):
    monkeypatch.setattr("app.api.routes.settings.urlopen", lambda *args, **kwargs: BytesIO(b'{"ready":"private-credential"}'))
    response = update(settings_api, {"apiKey": "private-credential"})
    assert response.status_code == 502
    assert "private-credential" not in response.text


def test_rotation_does_not_claim_live_mode_is_enabled(settings_api, monkeypatch):
    monkeypatch.setattr("app.api.routes.settings.urlopen", lambda *args, **kwargs: BytesIO(
        json.dumps(status_payload(enabled=False, ready=False)).encode(),
    ))
    response = update(settings_api, {"apiKey": "private-credential"})
    assert response.status_code == 200
    assert response.json()["ready"] is False
    assert response.json()["llm"]["enabled"] is False
    assert response.json()["llm"]["tokenConfigured"] is True


@pytest.mark.parametrize("method", ["GET", "PUT"])
def test_generic_settings_require_auth(settings_api, method):
    response = settings_api.request(method, "/settings/llm", json={"provider": "anthropic", "modelId": "claude-haiku-4-5"})
    assert response.status_code == 401


def test_generic_status_forwarding_filters_sensitive_and_unknown_fields(settings_api, monkeypatch):
    calls = []
    payload = status_payload(
        provider="anthropic", modelId="claude-haiku-4-5", apiKey="private-credential",
        models={"bedrock": "test-bedrock-model", "anthropic": "claude-haiku-4-5", "apiKey": "private-credential"},
        credentialsConfigured={"bedrock": True, "anthropic": True, "apiKey": "private-credential"},
    )
    def runtime(request, timeout):
        calls.append(request)
        return BytesIO(json.dumps(payload).encode())
    monkeypatch.setattr("app.api.routes.settings.urlopen", runtime)
    response = settings_api.get("/settings/llm", headers={"X-API-Key": "settings-test-key"})
    assert response.status_code == 200
    assert calls[0].method == "GET"
    assert calls[0].data is None
    assert calls[0].full_url == "http://runtime.test:8010/settings/llm"
    assert calls[0].get_header("X-ai-service-secret") == "runtime-shared-secret"
    assert response.json()["llm"]["provider"] == "anthropic"
    assert response.json()["llm"]["credentialsConfigured"] == {"bedrock": True, "anthropic": True}
    assert "private-credential" not in response.text
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("key,expected", [(None, None), ("", None), ("   ", None), ("  private-credential  ", "private-credential")])
def test_generic_update_forwards_selection_and_preserves_optional_key(settings_api, monkeypatch, key, expected):
    calls = []
    def runtime(request, timeout):
        calls.append(request)
        return BytesIO(json.dumps(status_payload(provider="anthropic", modelId="claude-haiku-4-5")).encode())
    monkeypatch.setattr("app.api.routes.settings.urlopen", runtime)
    body = {"provider": "anthropic", "modelId": "  claude-haiku-4-5  ", "ignoredKey": "not-forwarded"}
    if key is not None:
        body["apiKey"] = key
    response = settings_api.put("/settings/llm", json=body, headers={"X-API-Key": "settings-test-key"})
    assert response.status_code == 200
    forwarded = {"provider": "anthropic", "modelId": "claude-haiku-4-5"}
    if expected:
        forwarded["apiKey"] = expected
    assert json.loads(calls[0].data) == forwarded
    assert calls[0].method == "PUT"
    assert calls[0].full_url == "http://runtime.test:8010/settings/llm"
    assert "private-credential" not in response.text


@pytest.mark.parametrize("body", [
    None, [], {}, {"provider": []}, {"provider": {}}, {"provider": "unknown"},
    {"provider": "anthropic"}, {"provider": "anthropic", "modelId": ""},
    {"provider": "anthropic", "modelId": "secret value"},
    {"provider": "anthropic", "modelId": "secret\u200bvalue"},
    {"provider": "anthropic", "modelId": "x" * 513},
    {"provider": "anthropic", "modelId": "claude-haiku-4-5", "apiKey": 7},
    {"provider": "anthropic", "modelId": "claude-haiku-4-5", "apiKey": "secret value"},
])
def test_generic_invalid_selection_is_sanitized(settings_api, monkeypatch, body):
    def no_forward(*args, **kwargs):
        pytest.fail("Invalid settings must not reach the runtime")
    monkeypatch.setattr("app.api.routes.settings.urlopen", no_forward)
    response = settings_api.put("/settings/llm", json=body, headers={"X-API-Key": "settings-test-key"})
    assert response.status_code == 400
    assert "secret value" not in response.text


def test_generic_missing_provider_credential_error_is_sanitized(settings_api, monkeypatch):
    def runtime(*args, **kwargs):
        raise HTTPError("http://runtime.test", 400, "private-credential", {}, BytesIO(b"private-credential"))
    monkeypatch.setattr("app.api.routes.settings.urlopen", runtime)
    response = settings_api.put("/settings/llm", json={"provider": "anthropic", "modelId": "claude-haiku-4-5"}, headers={"X-API-Key": "settings-test-key"})
    assert response.status_code == 400
    assert "provider, model and API key" in response.text
    assert "private-credential" not in response.text
