from fastapi.testclient import TestClient
from botocore.awsrequest import AWSResponse
import json
import os
from types import SimpleNamespace

from app import main
from app.core.config import Settings
from app.services import conversation_titles as titles


def test_title_uses_selected_model_without_execution_instrumentation(monkeypatch):
    used = []
    settings = Settings(enable_live_llm=True, model_provider="anthropic", anthropic_api_key="test-only")
    monkeypatch.setattr(titles, "create_model", lambda selected, **kwargs: used.append(selected) or object())
    class FakeAgent:
        def __init__(self, **kwargs):
            assert kwargs["callback_handler"] is None
            assert kwargs["retry_strategy"] is None
        def __call__(self, prompt):
            assert "dipirona" in prompt
            return '"Consulta de estoque de dipirona"'
    monkeypatch.setattr(titles, "Agent", FakeAgent)
    assert titles.generate_title("Tem dipirona?", settings) == {"title": "Consulta de estoque de dipirona", "source": "model"}
    assert used[0].model_provider == "anthropic"
    assert used[0].llm_max_tokens == 48 and used[0].runtime_timeout_seconds == 7


def test_title_failure_falls_back(monkeypatch):
    def fail(*_args, **_kwargs):
        raise RuntimeError("Provider unavailable")
    monkeypatch.setattr(titles, "create_model", fail)
    result = titles.generate_title("Tem dipirona?", Settings(enable_live_llm=True, aws_bearer_token_bedrock="test-only"))
    assert result == {"title": "Tem dipirona?", "source": "fallback"}


def test_title_endpoint_authorization_validation_and_response(monkeypatch):
    monkeypatch.setattr(main, "get_settings", lambda: Settings(ai_service_secret="test-secret"))
    monkeypatch.setattr(main, "configure_telemetry", lambda _settings: None)
    monkeypatch.setattr(main, "generate_title", lambda text, _settings: {"title": text, "source": "model"})
    client = TestClient(main.create_app())
    headers = {"X-AI-Service-Secret": "test-secret"}
    assert client.post("/conversations/title", json={"text": "ignored"}).status_code == 403
    result = client.post("/conversations/title", json={"text": "Consulta de estoque"}, headers=headers)
    assert result.status_code == 200 and result.json()["title"] == "Consulta de estoque"
    assert result.headers["Cache-Control"] == "no-store"
    invalid = client.post("/conversations/title", json={"text": ""}, headers=headers)
    assert invalid.status_code == 400


def test_bedrock_title_signs_with_snapshot_key_after_rotation(monkeypatch):
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "stale-startup-key")
    used = []
    class LocalAgent:
        def __init__(self, model, **_kwargs):
            self.model = model
            def respond(request):
                used.append(request)
                assert request.headers["Authorization"] == b"Bearer rotated-title-key"
                body = {"output": {"message": {"role": "assistant", "content": [{"text": "Estoque de dipirona"}]}},
                        "stopReason": "end_turn", "usage": {"inputTokens": 2, "outputTokens": 3, "totalTokens": 5},
                        "metrics": {"latencyMs": 1}}
                raw = SimpleNamespace(stream=lambda **_: iter([json.dumps(body).encode()]))
                return AWSResponse(request.url, 200, {"content-type": "application/json"}, raw)
            model.client._endpoint.http_session.send = respond
        def __call__(self, _prompt):
            result = self.model.client.converse(modelId=self.model.config["model_id"],
                     messages=[{"role": "user", "content": [{"text": "Title only"}]}])
            return result["output"]["message"]["content"][0]["text"]
    monkeypatch.setattr(titles, "Agent", LocalAgent)
    result = titles.generate_title("Tem dipirona?", Settings(enable_live_llm=True,
                                   aws_bearer_token_bedrock="rotated-title-key", aws_region="us-east-1"))
    assert result == {"title": "Estoque de dipirona", "source": "model"}
    assert len(used) == 1
    assert os.environ["AWS_BEARER_TOKEN_BEDROCK"] == "stale-startup-key"
