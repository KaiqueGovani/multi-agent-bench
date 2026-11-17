"""Server-side credential updates; provider keys never become application data."""
import json
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request as RuntimeRequest, urlopen

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import Field, StrictBool, ValidationError
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.schemas.domain import ApiModel

router = APIRouter()


class ProviderModels(ApiModel):
    bedrock: str = ""
    anthropic: str = ""


class ProviderCredentials(ApiModel):
    bedrock: StrictBool = False
    anthropic: StrictBool = False


class LlmRuntimeStatus(ApiModel):
    enabled: StrictBool
    token_configured: StrictBool
    sdk_available: StrictBool
    ready: StrictBool
    model_id: str
    region: str
    provider: Literal["bedrock", "anthropic"] = "bedrock"
    models: ProviderModels = Field(default_factory=ProviderModels)
    credentials_configured: ProviderCredentials = Field(default_factory=ProviderCredentials)


class RuntimeSettingsResponse(ApiModel):
    mode: str
    runtime_url: str
    reachable: bool
    ready: bool
    llm: LlmRuntimeStatus
    error: str | None


@router.put("/bedrock", response_model=RuntimeSettingsResponse)
async def update_bedrock_key(request: Request, response: Response) -> RuntimeSettingsResponse:
    # Parse explicitly so FastAPI validation errors cannot include the key input.
    payload = await _read_settings_body(request)
    key = payload.get("apiKey") if isinstance(payload, dict) else None
    if not isinstance(key, str):
        raise HTTPException(status_code=400, detail="Provide a Bedrock API key in apiKey.")
    key = key.strip()
    if not key or len(key) > 16384 or any(char.isspace() or not char.isprintable() for char in key):
        raise HTTPException(status_code=400, detail="Provide a nonempty Bedrock API key without whitespace.")

    result = await run_in_threadpool(_runtime_settings_request, "/settings/bedrock", "PUT", {"apiKey": key})
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get("/llm", response_model=RuntimeSettingsResponse)
async def get_llm_settings(response: Response) -> RuntimeSettingsResponse:
    result = await run_in_threadpool(_runtime_settings_request, "/settings/llm", "GET")
    response.headers["Cache-Control"] = "no-store"
    return result


@router.put("/llm", response_model=RuntimeSettingsResponse)
async def update_llm_settings(request: Request, response: Response) -> RuntimeSettingsResponse:
    payload = await _read_settings_body(request)
    if not isinstance(payload, dict) or not isinstance(payload.get("provider"), str) or payload["provider"] not in {"bedrock", "anthropic"}:
        raise HTTPException(status_code=400, detail="Select the Bedrock or Anthropic provider.")
    model = payload.get("modelId")
    if not isinstance(model, str) or not model.strip() or len(model.strip()) > 512 or any(
        char.isspace() or not char.isprintable() for char in model.strip()
    ):
        raise HTTPException(status_code=400, detail="Provide a valid model ID without whitespace.")
    forwarded = {"provider": payload["provider"], "modelId": model.strip()}
    key = payload.get("apiKey")
    if key is not None:
        if not isinstance(key, str):
            raise HTTPException(status_code=400, detail="Provide a valid API key or leave it blank to keep the current key.")
        key = key.strip()
        if len(key) > 16384 or any(char.isspace() or not char.isprintable() for char in key):
            raise HTTPException(status_code=400, detail="Provide an API key without whitespace.")
        if key:
            forwarded["apiKey"] = key
    result = await run_in_threadpool(_runtime_settings_request, "/settings/llm", "PUT", forwarded)
    response.headers["Cache-Control"] = "no-store"
    return result


async def _read_settings_body(request: Request):
    # Keep submitted credentials out of validation errors, including bad JSON.
    body = await request.body()
    try:
        return json.loads(body) if len(body) <= 20 * 1024 else None
    except (ValueError, UnicodeDecodeError):
        return None


def _runtime_settings_request(path: str, method: str, payload: dict | None = None) -> RuntimeSettingsResponse:
    settings = get_settings()
    if not settings.ai_runtime_url:
        raise HTTPException(status_code=503, detail="Configure AI_RUNTIME_URL before using LLM settings.")

    headers = {"Content-Type": "application/json"}
    if settings.ai_service_secret:
        headers["X-AI-Service-Secret"] = settings.ai_service_secret
    try:
        upstream = RuntimeRequest(
            settings.ai_runtime_url.rstrip("/") + path,
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
            headers=headers,
            method=method,
        )
        with urlopen(upstream, timeout=settings.ai_runtime_timeout_seconds) as runtime_response:
            llm = LlmRuntimeStatus.model_validate_json(runtime_response.read())
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise HTTPException(
                status_code=503,
                detail="The runtime refused the update. Check AI_SERVICE_SECRET on the API and runtime.",
            ) from None
        if exc.code in {400, 422}:
            raise HTTPException(status_code=400, detail="The runtime rejected the LLM settings. Check the provider, model and API key.") from None
        raise HTTPException(status_code=502, detail="The runtime could not apply the LLM settings.") from None
    except (URLError, OSError, TimeoutError):
        raise HTTPException(status_code=503, detail="The agent runtime is unavailable. Try again when it is running.") from None
    except (ValidationError, ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=502, detail="The runtime returned an invalid settings response.") from None

    return RuntimeSettingsResponse(
        mode=settings.runtime_mode,
        runtime_url=settings.ai_runtime_url,
        reachable=True,
        ready=llm.ready,
        llm=llm,
        error=None if llm.ready else "Agent runtime is reachable, but live LLM is not ready.",
    )
