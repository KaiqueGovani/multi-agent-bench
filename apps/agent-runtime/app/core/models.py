"""Provider-specific Strands construction shared by all architectures."""
import os
from typing import Any

from strands.models.bedrock import BedrockModel

try:
    from strands.models.anthropic import AnthropicModel
except ImportError:  # pragma: no cover - reports missing optional SDK cleanly
    AnthropicModel = None

from app.core.config import Settings


def get_model_id(settings: Settings) -> str:
    if settings.model_provider == "anthropic":
        return settings.anthropic_model_id
    if settings.model_provider == "bedrock":
        return settings.bedrock_model_id
    raise ValueError("Unsupported model provider")


def get_api_key(settings: Settings) -> str | None:
    if settings.model_provider == "anthropic":
        return settings.anthropic_api_key
    if settings.model_provider == "bedrock":
        return settings.aws_bearer_token_bedrock
    return None


def model_kwargs(settings: Settings, **overrides: Any) -> dict[str, Any]:
    """Map common options to each provider's supported constructor arguments.

    The isolated worker receives its accepted credential through the environment;
    its serialized Settings deliberately omit credentials.
    """
    options = {
        "model_id": get_model_id(settings),
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
        **overrides,
    }
    if settings.model_provider == "bedrock":
        return {"region_name": settings.aws_region, **options}
    if settings.model_provider != "anthropic":
        raise ValueError("Unsupported model provider")

    options.pop("boto_client_config", None)
    options.pop("region_name", None)
    options.pop("streaming", None)  # AnthropicModel always uses normalized streaming.
    temperature = options.pop("temperature")
    stop_sequences = options.pop("stop_sequences", None)
    params = {"temperature": temperature, **options.pop("params", {})}
    if stop_sequences:
        params["stop_sequences"] = stop_sequences
    return {
        **options,
        "params": params,
        "client_args": {
            "api_key": settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY"),
            "timeout": settings.runtime_timeout_seconds,
            "max_retries": 0,
        },
    }


def create_model(settings: Settings, **overrides: Any) -> Any:
    if settings.model_provider == "anthropic":
        if AnthropicModel is None:
            raise RuntimeError("Anthropic model support is unavailable")
        return AnthropicModel(**model_kwargs(settings, **overrides))
    if settings.model_provider == "bedrock":
        return BedrockModel(**model_kwargs(settings, **overrides))
    raise ValueError("Unsupported model provider")
