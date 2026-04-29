import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = "Multi-Agent Pharmacy POC API"
    app_version: str = "0.1.0"
    environment: str = "local"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/multi_agent_bench"
    local_storage_path: str = str(Path("var") / "storage")
    storage_provider: str = "local"
    storage_bucket: str = "multi-agent-bench-poc"
    storage_endpoint_url: str | None = None
    storage_access_key: str | None = None
    storage_secret_key: str | None = None
    storage_region: str = "us-east-1"
    storage_addressing_style: str = "path"
    default_channel: str = "web_chat"
    default_architecture_mode: str = "centralized_orchestration"
    default_architecture_family: str = "orchestration"
    default_architecture_version: str = "poc"
    default_routing_strategy: str = "central_router"
    default_memory_strategy: str = "session_only"
    default_tool_executor_mode: str = "sequential"
    default_review_policy_version: str = "mock-review-v1"
    default_model_provider: str = "mock"
    default_model_name: str = "mock-agent-runtime"
    default_model_version: str = "poc"
    default_prompt_bundle_version: str = "mock-prompts-v1"
    default_toolset_version: str = "mock-tools-v1"
    default_experiment_id: str = "poc-local"
    runtime_mode: str = "mock"
    mock_runtime_step_delay_seconds: float = 0.9
    ai_runtime_url: str | None = None
    ai_runtime_timeout_seconds: int = 10
    app_base_url: str = "http://127.0.0.1:8000"
    runtime_history_window_messages: int = 8
    log_level: str = "INFO"
    api_key: str | None = None
    internal_secret: str | None = None
    ai_service_secret: str | None = None
    max_files_per_message: int = 4
    max_file_size_bytes: int = 5 * 1024 * 1024
    cors_allowed_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", Settings.app_name),
        app_version=os.getenv("APP_VERSION", Settings.app_version),
        environment=os.getenv("APP_ENV", Settings.environment),
        database_url=os.getenv("DATABASE_URL", Settings.database_url),
        local_storage_path=os.getenv("LOCAL_STORAGE_PATH", Settings.local_storage_path),
        storage_provider=os.getenv("STORAGE_PROVIDER", Settings.storage_provider),
        storage_bucket=os.getenv("STORAGE_BUCKET", Settings.storage_bucket),
        storage_endpoint_url=os.getenv("STORAGE_ENDPOINT_URL") or Settings.storage_endpoint_url,
        storage_access_key=os.getenv("STORAGE_ACCESS_KEY") or Settings.storage_access_key,
        storage_secret_key=os.getenv("STORAGE_SECRET_KEY") or Settings.storage_secret_key,
        storage_region=os.getenv("STORAGE_REGION", Settings.storage_region),
        storage_addressing_style=os.getenv(
            "STORAGE_ADDRESSING_STYLE",
            Settings.storage_addressing_style,
        ),
        default_channel=os.getenv("DEFAULT_CHANNEL", Settings.default_channel),
        default_architecture_mode=os.getenv(
            "DEFAULT_ARCHITECTURE_MODE",
            Settings.default_architecture_mode,
        ),
        default_architecture_family=os.getenv(
            "DEFAULT_ARCHITECTURE_FAMILY",
            Settings.default_architecture_family,
        ),
        default_architecture_version=os.getenv(
            "DEFAULT_ARCHITECTURE_VERSION",
            Settings.default_architecture_version,
        ),
        default_routing_strategy=os.getenv(
            "DEFAULT_ROUTING_STRATEGY",
            Settings.default_routing_strategy,
        ),
        default_memory_strategy=os.getenv(
            "DEFAULT_MEMORY_STRATEGY",
            Settings.default_memory_strategy,
        ),
        default_tool_executor_mode=os.getenv(
            "DEFAULT_TOOL_EXECUTOR_MODE",
            Settings.default_tool_executor_mode,
        ),
        default_review_policy_version=os.getenv(
            "DEFAULT_REVIEW_POLICY_VERSION",
            Settings.default_review_policy_version,
        ),
        default_model_provider=os.getenv("DEFAULT_MODEL_PROVIDER", Settings.default_model_provider),
        default_model_name=os.getenv("DEFAULT_MODEL_NAME", Settings.default_model_name),
        default_model_version=os.getenv("DEFAULT_MODEL_VERSION", Settings.default_model_version),
        default_prompt_bundle_version=os.getenv(
            "DEFAULT_PROMPT_BUNDLE_VERSION",
            Settings.default_prompt_bundle_version,
        ),
        default_toolset_version=os.getenv("DEFAULT_TOOLSET_VERSION", Settings.default_toolset_version),
        default_experiment_id=os.getenv("DEFAULT_EXPERIMENT_ID", Settings.default_experiment_id),
        runtime_mode=os.getenv("RUNTIME_MODE", Settings.runtime_mode),
        mock_runtime_step_delay_seconds=float(
            os.getenv(
                "MOCK_RUNTIME_STEP_DELAY_SECONDS",
                Settings.mock_runtime_step_delay_seconds,
            )
        ),
        ai_runtime_url=os.getenv("AI_RUNTIME_URL") or Settings.ai_runtime_url,
        ai_runtime_timeout_seconds=int(
            os.getenv("AI_RUNTIME_TIMEOUT_SECONDS", Settings.ai_runtime_timeout_seconds)
        ),
        app_base_url=os.getenv("APP_BASE_URL", Settings.app_base_url),
        runtime_history_window_messages=int(
            os.getenv(
                "RUNTIME_HISTORY_WINDOW_MESSAGES",
                Settings.runtime_history_window_messages,
            )
        ),
        log_level=os.getenv("LOG_LEVEL", Settings.log_level),
        api_key=os.getenv("API_KEY") or Settings.api_key,
        internal_secret=os.getenv("INTERNAL_SECRET") or Settings.internal_secret,
        ai_service_secret=os.getenv("AI_SERVICE_SECRET") or Settings.ai_service_secret,
        max_files_per_message=int(os.getenv("MAX_FILES_PER_MESSAGE", Settings.max_files_per_message)),
        max_file_size_bytes=int(os.getenv("MAX_FILE_SIZE_BYTES", Settings.max_file_size_bytes)),
        cors_allowed_origins=os.getenv("CORS_ALLOWED_ORIGINS", Settings.cors_allowed_origins),
    )
