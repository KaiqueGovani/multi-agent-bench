import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.api import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        runtime=build_runtime_status(),
    )


def build_runtime_status() -> dict:
    settings = get_settings()
    status = {
        "mode": settings.runtime_mode,
        "runtimeUrl": settings.ai_runtime_url,
        "reachable": False,
        "ready": False,
        "llm": None,
        "error": None,
    }
    if settings.runtime_mode != "real":
        status["error"] = "API is configured for mock runtime mode."
        return status
    if not settings.ai_runtime_url:
        status["error"] = "AI_RUNTIME_URL is not configured."
        return status

    try:
        with urlopen(settings.ai_runtime_url.rstrip("/") + "/health", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, OSError, json.JSONDecodeError) as exc:
        status["error"] = str(exc)
        return status

    llm_status = payload.get("llm") if isinstance(payload, dict) else None
    status["reachable"] = True
    status["llm"] = llm_status
    status["ready"] = bool(isinstance(llm_status, dict) and llm_status.get("ready"))
    if not status["ready"]:
        status["error"] = "Agent runtime is reachable, but live LLM is not ready."
    return status
