import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    app_name: str = "Multi-Agent Pharmacy POC API"
    app_version: str = "0.1.0"
    environment: str = "local"
    default_channel: str = "web_chat"
    default_architecture_mode: str = "centralized_orchestration"
    runtime_mode: str = "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", Settings.app_name),
        app_version=os.getenv("APP_VERSION", Settings.app_version),
        environment=os.getenv("APP_ENV", Settings.environment),
        default_channel=os.getenv("DEFAULT_CHANNEL", Settings.default_channel),
        default_architecture_mode=os.getenv(
            "DEFAULT_ARCHITECTURE_MODE",
            Settings.default_architecture_mode,
        ),
        runtime_mode=os.getenv("RUNTIME_MODE", Settings.runtime_mode),
    )

