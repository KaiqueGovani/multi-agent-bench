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
    default_channel: str = "web_chat"
    default_architecture_mode: str = "centralized_orchestration"
    runtime_mode: str = "mock"
    max_files_per_message: int = 4
    max_file_size_bytes: int = 5 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", Settings.app_name),
        app_version=os.getenv("APP_VERSION", Settings.app_version),
        environment=os.getenv("APP_ENV", Settings.environment),
        database_url=os.getenv("DATABASE_URL", Settings.database_url),
        local_storage_path=os.getenv("LOCAL_STORAGE_PATH", Settings.local_storage_path),
        default_channel=os.getenv("DEFAULT_CHANNEL", Settings.default_channel),
        default_architecture_mode=os.getenv(
            "DEFAULT_ARCHITECTURE_MODE",
            Settings.default_architecture_mode,
        ),
        runtime_mode=os.getenv("RUNTIME_MODE", Settings.runtime_mode),
        max_files_per_message=int(os.getenv("MAX_FILES_PER_MESSAGE", Settings.max_files_per_message)),
        max_file_size_bytes=int(os.getenv("MAX_FILE_SIZE_BYTES", Settings.max_file_size_bytes)),
    )
