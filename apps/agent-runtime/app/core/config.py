import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = "Multi-Agent Bench Agent Runtime"
    app_version: str = "0.1.0"
    environment: str = "local"
    log_level: str = "INFO"
    bedrock_model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    aws_region: str = "us-east-1"
    aws_bearer_token_bedrock: str | None = None
    enable_live_llm: bool = False
    enable_otel: bool = False
    otel_exporter_otlp_endpoint: str | None = None
    otel_service_name: str = "multi-agent-bench-agent-runtime"
    default_architecture_mode: str = "centralized_orchestration"
    default_review_policy_version: str = "strands-review-v1"
    runtime_max_handoffs: int = 6
    runtime_timeout_seconds: int = 45
    chat_api_callback_timeout_seconds: int = 10


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", Settings.app_name),
        app_version=os.getenv("APP_VERSION", Settings.app_version),
        environment=os.getenv("APP_ENV", Settings.environment),
        log_level=os.getenv("LOG_LEVEL", Settings.log_level),
        bedrock_model_id=os.getenv("BEDROCK_MODEL_ID", Settings.bedrock_model_id),
        aws_region=os.getenv("AWS_REGION", Settings.aws_region),
        aws_bearer_token_bedrock=os.getenv("AWS_BEARER_TOKEN_BEDROCK") or Settings.aws_bearer_token_bedrock,
        enable_live_llm=_as_bool(os.getenv("ENABLE_LIVE_LLM"), Settings.enable_live_llm),
        enable_otel=_as_bool(os.getenv("ENABLE_OTEL"), Settings.enable_otel),
        otel_exporter_otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or Settings.otel_exporter_otlp_endpoint,
        otel_service_name=os.getenv("OTEL_SERVICE_NAME", Settings.otel_service_name),
        default_architecture_mode=os.getenv("DEFAULT_ARCHITECTURE_MODE", Settings.default_architecture_mode),
        default_review_policy_version=os.getenv(
            "DEFAULT_REVIEW_POLICY_VERSION",
            Settings.default_review_policy_version,
        ),
        runtime_max_handoffs=int(os.getenv("RUNTIME_MAX_HANDOFFS", Settings.runtime_max_handoffs)),
        runtime_timeout_seconds=int(os.getenv("RUNTIME_TIMEOUT_SECONDS", Settings.runtime_timeout_seconds)),
        chat_api_callback_timeout_seconds=int(
            os.getenv(
                "CHAT_API_CALLBACK_TIMEOUT_SECONDS",
                Settings.chat_api_callback_timeout_seconds,
            )
        ),
    )
