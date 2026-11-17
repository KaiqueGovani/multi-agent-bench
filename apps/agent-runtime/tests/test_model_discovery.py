import asyncio
import json
from types import SimpleNamespace

from anthropic import AsyncAnthropic
from botocore.awsrequest import AWSResponse
import httpx
import pytest

from app.services import model_discovery as discovery
from app.core.config import Settings
from test_runtime_settings import runtime


def model(model_id, name="Claude Test"):
    return {"id": model_id, "display_name": name, "type": "model", "created_at": "2026-01-01T00:00:00Z"}


def anthropic_transport(monkeypatch, handler):
    constructed = []

    def create(**kwargs):
        constructed.append(kwargs)
        return AsyncAnthropic(**kwargs, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    monkeypatch.setattr(discovery, "AsyncAnthropic", create)
    return constructed


def test_anthropic_lists_using_unsaved_key_without_changing_runtime(runtime, monkeypatch):
    initial, _, client = runtime
    headers = {"X-AI-Service-Secret": initial.ai_service_secret}
    requests = []

    def respond(request):
        requests.append(request)
        assert request.url.path == "/v1/models"
        assert request.headers["x-api-key"] == "unsaved-discovery-key"
        if len(requests) == 1:
            return httpx.Response(200, json={"data": [model("claude-one")], "has_more": True, "last_id": "claude-one"})
        assert request.url.params["after_id"] == "claude-one"
        return httpx.Response(200, json={"data": [model("claude-one"), model("claude-two", "Claude Second")], "has_more": False})

    configured = anthropic_transport(monkeypatch, respond)
    before = client.get("/settings/llm", headers=headers).json()
    result = client.post("/settings/llm/models", json={"provider": "anthropic", "apiKey": "unsaved-discovery-key"}, headers=headers)
    assert result.status_code == 200
    assert result.headers["cache-control"] == "no-store"
    assert result.json() == {"provider": "anthropic", "source": "provider", "models": [
        {"id": "claude-one", "name": "Claude Test"}, {"id": "claude-two", "name": "Claude Second"}]}
    assert configured == [{"api_key": "unsaved-discovery-key", "timeout": 5, "max_retries": 0}]
    assert client.get("/settings/llm", headers=headers).json() == before
    assert "unsaved-discovery-key" not in result.text


def test_discovery_reuses_provider_key_without_selecting_provider(runtime, monkeypatch):
    initial, _, client = runtime
    headers = {"X-AI-Service-Secret": initial.ai_service_secret}
    client.put("/settings/llm", json={"provider": "anthropic", "modelId": "claude-test", "apiKey": "saved-direct-key"}, headers=headers)
    client.put("/settings/llm", json={"provider": "bedrock", "modelId": "bedrock-test", "apiKey": "saved-aws-key"}, headers=headers)
    selected = client.get("/settings/llm", headers=headers).json()

    def respond(request):
        assert request.headers["x-api-key"] == "saved-direct-key"
        return httpx.Response(200, json={"data": [model("claude-one")], "has_more": False})

    anthropic_transport(monkeypatch, respond)
    result = client.post("/settings/llm/models", json={"provider": "anthropic", "apiKey": " "}, headers=headers)
    assert result.status_code == 200
    assert client.get("/settings/llm", headers=headers).json() == selected


@pytest.mark.parametrize("response", [
    {"error": {"message": "upstream echoed private-key"}},
    {"data": [model("bad model id")], "has_more": False},
    {"data": [], "has_more": False},
    {"data": [model("claude-one")], "has_more": True},
])
def test_provider_errors_never_echo_response_or_key(runtime, monkeypatch, response):
    initial, _, client = runtime
    anthropic_transport(monkeypatch, lambda _: httpx.Response(401 if "error" in response else 200, json=response))
    result = client.post("/settings/llm/models", json={"provider": "anthropic", "apiKey": "private-key"},
                         headers={"X-AI-Service-Secret": initial.ai_service_secret})
    assert result.status_code == 502
    assert result.json() == {"detail": "Could not load models from Anthropic. Check the API key and try again."}
    assert "private-key" not in result.text


def test_anthropic_discovery_has_total_deadline(runtime, monkeypatch):
    initial, _, client = runtime

    async def wait_forever(_key):
        await asyncio.sleep(10)

    monkeypatch.setattr(discovery, "_anthropic_models", wait_forever)
    monkeypatch.setattr(discovery, "DISCOVERY_TIMEOUT_SECONDS", 0.01)
    result = client.post("/settings/llm/models", json={"provider": "anthropic", "apiKey": "private-key"},
                         headers={"X-AI-Service-Secret": initial.ai_service_secret})
    assert result.status_code == 504
    assert result.json() == {"detail": "Model discovery timed out. Try again."}


def test_anthropic_pagination_is_bounded(runtime, monkeypatch):
    initial, _, client = runtime
    requests = []

    def respond(request):
        requests.append(request)
        model_id = f"claude-page-{len(requests)}"
        return httpx.Response(200, json={"data": [model(model_id)], "has_more": True, "last_id": model_id})

    anthropic_transport(monkeypatch, respond)
    result = client.post("/settings/llm/models", json={"provider": "anthropic", "apiKey": "private-key"},
                         headers={"X-AI-Service-Secret": initial.ai_service_secret})
    assert result.status_code == 200
    assert len(requests) == discovery.MAX_ANTHROPIC_PAGES


def test_bedrock_sdk_signs_only_with_request_key_and_lists_active_claude_profiles(monkeypatch):
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "stale-environment-key")
    client = discovery._bedrock_client("request-specific-key", "us-east-1")
    requests = []

    def respond(request, **_kwargs):
        requests.append(request)
        assert request.headers["Authorization"] == b"Bearer request-specific-key"
        body = {"inferenceProfileSummaries": [
            {"inferenceProfileId": "us.anthropic.claude-valid", "inferenceProfileName": "Claude Valid", "status": "ACTIVE"},
            {"inferenceProfileId": "us.anthropic.claude-inactive", "inferenceProfileName": "Inactive", "status": "INACTIVE"},
            {"inferenceProfileId": "us.amazon.other", "inferenceProfileName": "Other", "status": "ACTIVE"},
        ]}
        raw = SimpleNamespace(stream=lambda **_: iter([json.dumps(body).encode()]))
        return AWSResponse(request.url, 200, {"content-type": "application/json"}, raw)

    client.meta.events.register("before-send.bedrock.ListInferenceProfiles", respond)
    monkeypatch.setattr(discovery, "_bedrock_client", lambda _key, _region: client)
    listed = asyncio.run(discovery.discover_models("bedrock", "request-specific-key", Settings()))
    assert listed.source == "provider"
    assert [option.model_dump() for option in listed.models] == [{"id": "us.anthropic.claude-valid", "name": "Claude Valid"}]
    assert len(requests) == 1
    assert "/inference-profiles" in requests[0].url


@pytest.mark.parametrize("region", ["us-east-1", "eu-west-1"])
def test_bedrock_missing_key_returns_honest_catalog_with_current_model(runtime, monkeypatch, region):
    initial, _, client = runtime
    monkeypatch.setattr(discovery, "_bedrock_models", lambda *_: pytest.fail("Catalog must not access a provider"))
    listing = asyncio.run(discovery.discover_models("bedrock", None, Settings(aws_region=region, bedrock_model_id="custom-profile")))
    assert listing.source == "catalog"
    assert listing.models[0].id == "custom-profile"
    if region == "us-east-1":
        assert "us.anthropic.claude-haiku-4-5-20251001-v1:0" in [option.id for option in listing.models]
    else:
        assert len(listing.models) == 1
    result = client.post("/settings/llm/models", json={"provider": "bedrock"},
                         headers={"X-AI-Service-Secret": initial.ai_service_secret})
    assert result.status_code == 200 and result.json()["source"] == "catalog"


def test_bedrock_discovery_failure_degrades_to_catalog_without_leaking_key(monkeypatch):
    def fail(*_):
        raise RuntimeError("upstream private-key")

    monkeypatch.setattr(discovery, "_bedrock_models", fail)
    listing = asyncio.run(discovery.discover_models("bedrock", "private-key", Settings()))
    assert listing.source == "catalog"
    assert "private-key" not in listing.model_dump_json()


def test_bedrock_pagination_is_bounded_and_client_closed(monkeypatch):
    calls, closed = [], []

    def page(**kwargs):
        calls.append(kwargs)
        index = len(calls)
        return {"inferenceProfileSummaries": [
            {"inferenceProfileId": f"us.anthropic.claude-page-{index}", "inferenceProfileName": f"Claude {index}", "status": "ACTIVE"}
        ], "nextToken": f"page-{index + 1}"}

    client = SimpleNamespace(list_inference_profiles=page, close=lambda: closed.append(True))
    monkeypatch.setattr(discovery, "_bedrock_client", lambda *_: client)
    listing = asyncio.run(discovery.discover_models("bedrock", "request-key", Settings()))
    assert listing.source == "provider"
    assert len(calls) == discovery.MAX_BEDROCK_PAGES
    assert calls[0] == {"typeEquals": "SYSTEM_DEFINED", "maxResults": 1000}
    assert calls[1]["nextToken"] == "page-2"
    assert closed == [True]


@pytest.mark.parametrize("payload", [None, [], {}, {"provider": []}, {"provider": "wrong"},
    {"provider": "anthropic", "apiKey": None}, {"provider": "anthropic", "apiKey": "bad key"},
    {"provider": "anthropic"}])
def test_invalid_or_missing_key_discovery_is_safe(runtime, payload):
    initial, _, client = runtime
    result = client.post("/settings/llm/models", json=payload,
                         headers={"X-AI-Service-Secret": initial.ai_service_secret})
    assert result.status_code == 400


def test_model_discovery_requires_settings_auth(runtime):
    _, _, client = runtime
    assert client.post("/settings/llm/models", json={"provider": "bedrock"}).status_code == 403
