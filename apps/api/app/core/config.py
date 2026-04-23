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
    runtime_mode: str = "mock"
    log_level: str = "INFO"
    api_key: str | None = None
    internal_secret: str | None = None
    ai_service_secret: str | None = None
    max_files_per_message: int = 4
    max_file_size_bytes: int = 5 * 1024 * 1024
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"


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
        runtime_mode=os.getenv("RUNTIME_MODE", Settings.runtime_mode),
        log_level=os.getenv("LOG_LEVEL", Settings.log_level),
        api_key=os.getenv("API_KEY") or Settings.api_key,
        internal_secret=os.getenv("INTERNAL_SECRET") or Settings.internal_secret,
        ai_service_secret=os.getenv("AI_SERVICE_SECRET") or Settings.ai_service_secret,
        max_files_per_message=int(os.getenv("MAX_FILES_PER_MESSAGE", Settings.max_files_per_message)),
        max_file_size_bytes=int(os.getenv("MAX_FILE_SIZE_BYTES", Settings.max_file_size_bytes)),
        cors_allowed_origins=os.getenv("CORS_ALLOWED_ORIGINS", Settings.cors_allowed_origins),
    )
