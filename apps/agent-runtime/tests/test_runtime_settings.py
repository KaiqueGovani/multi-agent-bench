from concurrent.futures import Future
import os

from fastapi.testclient import TestClient
import pytest

from app import main
from app.core.config import Settings
from test_runtime_service import build_request


@pytest.fixture
def runtime(monkeypatch):
    initial = Settings(enable_live_llm=True, ai_service_secret="runtime-test-secret")
    monkeypatch.setattr(main, "get_settings", lambda: initial)
    monkeypatch.setattr(main, "configure_telemetry", lambda _: None)
    monkeypatch.setattr(main, "Agent", object())
    monkeypatch.setattr(main, "BedrockModel", object())
    monkeypatch.setattr(main, "AnthropicModel", object())
    queued = []

    class Queue:
        def submit(self, execute, request):
            queued.append((execute.__self__, request))
            return Future()

    monkeypatch.setattr(main, "_executor", Queue())
    return initial, queued, TestClient(main.create_app(), client=("127.0.0.1", 50000))


def test_rotation_uses_new_key_for_later_runs_and_keeps_accepted_snapshot(runtime):
    initial, queued, client = runtime
    headers = {"X-AI-Service-Secret": initial.ai_service_secret}
    request = build_request().model_dump(mode="json", by_alias=True)
    environment_before = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")

    assert client.get("/health").json()["llm"]["tokenConfigured"] is False
    assert client.post("/runs", json=request).status_code == 503
    first = client.put("/settings/bedrock", json={"apiKey": "  first-token  "}, headers=headers)
    assert first.status_code == 200
    assert first.json()["ready"] is True
    assert first.headers["cache-control"] == "no-store"
    assert client.post("/runs", json=request).status_code == 202

    second = client.put("/settings/bedrock", json={"apiKey": "replacement-token"}, headers=headers)
    assert second.status_code == 200
    assert client.post("/runs", json=request).status_code == 202
    assert [service._settings.aws_bearer_token_bedrock for service, _ in queued] == [
        "first-token", "replacement-token"
    ]
    assert all(service._isolate_live for service, _ in queued)
    assert initial.aws_bearer_token_bedrock is None
    assert os.environ.get("AWS_BEARER_TOKEN_BEDROCK") == environment_before
    assert "replacement-token" not in second.text
    assert "replacement-token" not in client.get("/health").text
    assert "replacement-token" not in repr(queued[-1][0]._settings)
    assert initial.ai_service_secret not in repr(initial)
    # Rotation is scoped to this running application, not the environment/cache.
    restarted = TestClient(main.create_app())
    assert restarted.get("/health").json()["llm"]["tokenConfigured"] is False


@pytest.mark.parametrize("headers", [{}, {"X-AI-Service-Secret": "wrong-secret"}])
def test_shared_secret_required_when_configured(runtime, headers):
    _, _, client = runtime
    result = client.put("/settings/bedrock", json={"apiKey": "never-saved"}, headers=headers)
    assert result.status_code == 403
    assert "never-saved" not in result.text
    assert client.get("/health").json()["llm"]["tokenConfigured"] is False


@pytest.mark.parametrize("payload", [
    None, [], {"apiKey": None}, {"apiKey": 7}, {}, {"apiKey": ""},
    {"apiKey": "   "}, {"apiKey": "secret value"}, {"apiKey": "secret\nvalue"},
    {"apiKey": "secret\x00value"}, {"apiKey": "secret\x7fvalue"},
    {"apiKey": "secret\x9bvalue"}, {"apiKey": "secret\u200bvalue"},
    {"apiKey": "s" * 16385},
])
def test_invalid_key_does_not_echo_input_or_change_status(runtime, payload):
    initial, _, client = runtime
    result = client.put("/settings/bedrock", json=payload,
                        headers={"X-AI-Service-Secret": initial.ai_service_secret})
    assert result.status_code == 400
    assert result.json() == {"detail": "A valid Bedrock API key is required."}
    assert client.get("/health").json()["llm"]["tokenConfigured"] is False


def test_invalid_json_does_not_echo_body(runtime):
    initial, _, client = runtime
    result = client.put("/settings/bedrock", content='{"apiKey":"private-token"',
                        headers={"X-AI-Service-Secret": initial.ai_service_secret})
    assert result.status_code == 400
    assert "private-token" not in result.text


@pytest.mark.parametrize(("host", "headers", "expected"), [
    ("127.0.0.1", {}, 200), ("::1", {}, 200),
    ("127.0.0.1", {"Origin": "http://localhost:3100"}, 403),
    ("192.0.2.10", {}, 403), ("testclient", {}, 403),
])
def test_without_shared_secret_only_loopback_backend_calls_allowed(monkeypatch, host, headers, expected):
    monkeypatch.setattr(main, "get_settings", lambda: Settings(enable_live_llm=True))
    monkeypatch.setattr(main, "configure_telemetry", lambda _: None)
    client = TestClient(main.create_app(), client=(host, 50000))
    result = client.put("/settings/bedrock", json={"apiKey": "test-token"}, headers=headers)
    assert result.status_code == expected


def test_provider_switch_retains_keys_models_and_accepted_run_snapshots(runtime):
    initial, queued, client = runtime
    headers = {"X-AI-Service-Secret": initial.ai_service_secret}
    request = build_request().model_dump(mode="json", by_alias=True)
    request["experiment"].update(modelProvider="wrong-provider", modelName="wrong-model")

    bedrock = client.put("/settings/llm", json={"provider": "bedrock", "modelId": "bedrock-model",
                        "apiKey": "bedrock-key"}, headers=headers)
    assert bedrock.status_code == 200
    first = client.post("/runs", json=request)
    assert first.json()["modelProvider"] == "bedrock"
    assert first.json()["modelName"] == "bedrock-model"
    anthropic = client.put("/settings/llm", json={"provider": "anthropic", "modelId": "claude-custom",
                           "apiKey": "direct-key"}, headers=headers)
    assert anthropic.status_code == 200
    status = anthropic.json()
    assert status["provider"] == "anthropic" and status["modelId"] == "claude-custom"
    assert status["models"] == {"bedrock": "bedrock-model", "anthropic": "claude-custom"}
    assert status["credentialsConfigured"] == {"bedrock": True, "anthropic": True}
    second = client.post("/runs", json=request)
    assert second.json()["modelProvider"] == "anthropic"
    assert second.json()["modelName"] == "claude-custom"

    # Legacy credential rotation does not select Bedrock when Claude is active.
    legacy = client.put("/settings/bedrock", json={"apiKey": "updated-bedrock-key"}, headers=headers)
    assert legacy.json()["provider"] == "anthropic"
    switch_back = client.put("/settings/llm", json={"provider": "bedrock", "modelId": "next-bedrock"}, headers=headers)
    assert switch_back.status_code == 200
    assert client.post("/runs", json=request).status_code == 202
    reuse = client.put("/settings/llm", json={"provider": "anthropic", "modelId": "next-claude", "apiKey": " "}, headers=headers)
    assert reuse.status_code == 200
    assert client.post("/runs", json=request).status_code == 202

    assert [(service._settings.model_provider, service._settings.bedrock_model_id,
             service._settings.anthropic_model_id, service._settings.aws_bearer_token_bedrock,
             service._settings.anthropic_api_key) for service, _ in queued] == [
        ("bedrock", "bedrock-model", initial.anthropic_model_id, "bedrock-key", None),
        ("anthropic", "bedrock-model", "claude-custom", "bedrock-key", "direct-key"),
        ("bedrock", "next-bedrock", "claude-custom", "updated-bedrock-key", "direct-key"),
        ("anthropic", "next-bedrock", "next-claude", "updated-bedrock-key", "direct-key"),
    ]
    assert [(accepted.experiment.model_provider, accepted.experiment.model_name) for _, accepted in queued] == [
        ("bedrock", "bedrock-model"), ("anthropic", "claude-custom"),
        ("bedrock", "next-bedrock"), ("anthropic", "next-claude"),
    ]
    fetched = client.get("/settings/llm", headers=headers)
    assert fetched.headers["cache-control"] == "no-store"
    assert fetched.json() == client.get("/health").json()["llm"]
    for secret in ("bedrock-key", "updated-bedrock-key", "direct-key", initial.ai_service_secret):
        assert secret not in fetched.text
        assert secret not in repr(queued[-1][0]._settings)


@pytest.mark.parametrize("payload", [
    {}, [], None, {"provider": []}, {"provider": {}}, {"provider": "unsupported", "modelId": "id"},
    {"provider": "anthropic", "modelId": ""}, {"provider": "bedrock", "modelId": "bad model"},
    {"provider": "anthropic", "modelId": "id", "apiKey": None},
    {"provider": "anthropic", "modelId": "id", "apiKey": "bad key"},
    {"provider": "anthropic", "modelId": "id"},
])
def test_invalid_generic_settings_do_not_modify_active_snapshot(runtime, payload):
    initial, _, client = runtime
    headers = {"X-AI-Service-Secret": initial.ai_service_secret}
    before = client.get("/settings/llm", headers=headers).json()
    assert client.put("/settings/llm", json=payload, headers=headers).status_code == 400
    assert client.get("/settings/llm", headers=headers).json() == before


def test_generic_read_and_update_require_settings_authorization(runtime):
    _, _, client = runtime
    assert client.get("/settings/llm").status_code == 403
    assert client.put("/settings/llm", json={"provider": "anthropic", "modelId": "model", "apiKey": "secret"}).status_code == 403
