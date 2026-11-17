"""Real Strands Anthropic formatting with an entirely local response transport."""
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest
from strands.models.anthropic import AnthropicModel
from strands.models.bedrock import BedrockModel

from app.architectures import comparison as shared
from app.architectures import comparison_v43 as v43
from app.architectures import comparison_v44 as v44
from app.schemas.runtime import RuntimeAttachmentDescriptor
from test_research_comparison import context
from uuid import uuid4


class LocalStream:
    def __init__(self, content):
        self.content = content

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def __aiter__(self):
        def event(kind, **fields):
            value = {"type": kind, **fields}
            return SimpleNamespace(type=kind, model_dump=lambda: value)

        yield event("message_start")
        for index, block in enumerate(self.content):
            if block["type"] == "tool_use":
                yield event("content_block_start", index=index,
                            content_block={**block, "input": {}})
                yield event("content_block_delta", index=index,
                            delta={"type": "input_json_delta", "partial_json": json.dumps(block["input"])})
            else:
                yield event("content_block_start", index=index, content_block={"type": "text", "text": ""})
                yield event("content_block_delta", index=index,
                            delta={"type": "text_delta", "text": block["text"]})
            yield event("content_block_stop", index=index)
        stop = "tool_use" if any(block["type"] == "tool_use" for block in self.content) else "end_turn"
        yield SimpleNamespace(type="message_stop", message=SimpleNamespace(stop_reason=stop))

    async def get_final_message(self):
        return SimpleNamespace(usage=SimpleNamespace(model_dump=lambda: {"input_tokens": 7, "output_tokens": 3}))


def local_provider(monkeypatch):
    calls, constructors = [], []

    def initialize(model, **kwargs):
        constructors.append(kwargs)
        model.config = {key: value for key, value in kwargs.items() if key != "client_args"}
        model.client = SimpleNamespace(messages=SimpleNamespace(stream=lambda **request: respond(model, request)))

    def respond(model, request):
        calls.append((model.role, request))
        has_result = any(block.get("type") == "tool_result"
                         for message in request["messages"] for block in message["content"])
        if model.role in {"router", "coordinator"}:
            content = [{"type": "tool_use", "id": f"route-{len(calls)}",
                        "name": request["tools"][-1]["name"], "input": {"routes": ["faq"]}}]
        elif model.role == "supervisor" and not has_result:
            tool = request["tools"][0]["name"]
            content = [{"type": "tool_use", "id": f"delegate-{len(calls)}", "name": tool,
                        "input": {"task": "Consulte as evidências solicitadas"}}]
        elif model.role in shared.TOOLS and not has_result:
            name = shared.TOOLS[model.role].tool_spec["name"]
            arguments = {"attachments": []} if model.role == "attachments" else {"question": "horário"}
            content = [{"type": "tool_use", "id": f"source-{len(calls)}", "name": name, "input": arguments}]
        else:
            content = [{"type": "text", "text": "Evidências verificadas: atendimento das 08:00 às 22:00."}]
        return LocalStream(content)

    def forbid_bedrock(*args, **kwargs):
        raise AssertionError("A direct Anthropic execution must not construct BedrockModel")

    monkeypatch.setattr(AnthropicModel, "__init__", initialize)
    monkeypatch.setattr(BedrockModel, "__init__", forbid_bedrock)
    return calls, constructors


@pytest.mark.parametrize("execute", [shared.execute_comparison, v43.execute_comparison_v43, v44.execute_comparison_v44])
@pytest.mark.parametrize("architecture", shared.ARCHITECTURES)
def test_direct_anthropic_comparisons_preserve_tools_and_physical_usage(monkeypatch, execute, architecture):
    calls, constructors = local_provider(monkeypatch)
    ctx = context(architecture)
    ctx.settings = replace(ctx.settings, model_provider="anthropic", anthropic_api_key="synthetic-anthropic-key")

    result = execute(ctx, architecture)

    assert result.architectural_compliance
    assert result.total_tokens == 10 * len(calls)
    assert result.input_tokens == 7 * len(calls)
    assert result.output_tokens == 3 * len(calls)
    assert result.model_requests == len(calls)
    assert result.domain_tool_calls >= 1
    assert all(request["model"] == ctx.settings.anthropic_model_id for _, request in calls)
    assert all(not {"region_name", "boto_client_config", "streaming", "temperature"}.intersection(kwargs)
               for kwargs in constructors)
    assert all(kwargs["client_args"]["api_key"] == "synthetic-anthropic-key" for kwargs in constructors)
    assert all(kwargs["client_args"]["max_retries"] == 0 for kwargs in constructors)
    configuration = next(event.payload for event in ctx.callbacks.events
                         if event.event_family == "experiment" and event.event_name == "configuration")
    assert configuration["model_provider"] == "anthropic"
    assert configuration["model_id"] == ctx.settings.anthropic_model_id
    assert configuration["streaming"] is True
    assert "synthetic-anthropic-key" not in json.dumps(configuration)
    completed = [event for event in ctx.callbacks.events if event.event_family == "model" and event.event_name == "completed"]
    assert len(completed) == len(calls)
    assert all(event.payload["usage"]["totalTokens"] == 10 for event in completed)
    if architecture == "centralized_orchestration" and execute is not shared.execute_comparison:
        assert calls[0][1]["tool_choice"] == {"type": "any"}
        assert calls[-1][1].get("tool_choice", {"type": "auto"}) == {"type": "auto"}


@pytest.mark.parametrize("execute", [v43.execute_comparison_v43, v44.execute_comparison_v44])
def test_anthropic_first_turn_scope_enforces_attachment_specialist(monkeypatch, execute):
    calls, _ = local_provider(monkeypatch)
    ctx = context("centralized_orchestration")
    ctx.settings = replace(ctx.settings, model_provider="anthropic", anthropic_api_key="synthetic-key")
    message = ctx.request.latest_message
    message.attachments = [RuntimeAttachmentDescriptor(
        attachment_id=uuid4(), message_id=message.id, original_filename="document.pdf",
        mime_type="application/pdf", size_bytes=10, checksum="synthetic", retrieval_url="http://private.invalid/file",
    )]

    result = execute(ctx, "centralized_orchestration")

    assert result.architectural_compliance
    assert calls[0][1]["tool_choice"] == {"type": "any"}
    assert [tool["name"] for tool in calls[0][1]["tools"]] == ["attachments_specialist"]
    assert {tool["name"] for tool in calls[-1][1]["tools"]} == shared.SPECIALIST_NAMES
    assert all("private.invalid" not in json.dumps(request["messages"]) for _, request in calls)
