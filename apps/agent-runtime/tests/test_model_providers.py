from dataclasses import replace
from app.architectures import base
from app.core import models
from app.core.config import Settings
from test_research_comparison import context


def test_anthropic_factory_uses_direct_sdk_arguments_and_snapshot_key(monkeypatch):
    captured = []
    monkeypatch.setattr(models, "AnthropicModel", lambda **kwargs: captured.append(kwargs) or "direct-model")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "stale-environment-key")
    settings = Settings(model_provider="anthropic", anthropic_model_id="claude-custom",
                        anthropic_api_key="snapshot-key", llm_temperature=0.3, llm_max_tokens=256)
    assert models.create_model(settings) == "direct-model"
    kwargs = captured[0]
    assert kwargs == {"model_id": "claude-custom", "max_tokens": 256,
                      "params": {"temperature": 0.3},
                      "client_args": {"api_key": "snapshot-key", "timeout": 45, "max_retries": 0}}
    # Serialized child settings omit the credential and read the selected key from env.
    assert models.model_kwargs(replace(settings, anthropic_api_key=None))["client_args"]["api_key"] == "stale-environment-key"


def test_all_normal_agent_creation_paths_select_anthropic(monkeypatch):
    created = []
    model = object()
    monkeypatch.setattr(models, "AnthropicModel", lambda **kwargs: created.append(kwargs) or model)

    class Agent:
        def __init__(self, **kwargs):
            assert kwargs["model"] is model
        def __call__(self, prompt):
            return "Controlled response"

    monkeypatch.setattr(base, "Agent", Agent)
    ctx = context("centralized_orchestration")
    ctx.settings = replace(ctx.settings, model_provider="anthropic", anthropic_api_key="test-key")
    assert ctx.invoke_live_agent(system_prompt="prompt", prompt="question") == "Controlled response"
    assert ctx.invoke_live_supervisor(system_prompt="prompt", user_message="question", tools=[]) == ("Controlled response", [])
    assert ctx.create_agent(system_prompt="prompt", tools=[], actor_name="faq")("question") == "Controlled response"
    assert len(created) == 3
    assert all(kwargs["model_id"] == ctx.settings.anthropic_model_id for kwargs in created)
    assert all("region_name" not in kwargs and "boto_client_config" not in kwargs for kwargs in created)
