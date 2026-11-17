"""Server-side credential updates; provider keys never become application data."""
import json
from typing import Literal, TypeVar
from urllib.error import HTTPError, URLError
from urllib.request import Request as RuntimeRequest, urlopen

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import Field, StrictBool, ValidationError, field_validator
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.schemas.domain import ApiModel

router = APIRouter()
RuntimeResponseModel = TypeVar("RuntimeResponseModel", bound=ApiModel)


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


class AvailableModel(ApiModel):
    id: str = Field(min_length=1, max_length=512)
    name: str = Field(min_length=1, max_length=512)

    @field_validator("id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if any(character.isspace() or not character.isprintable() for character in value):
            raise ValueError("Invalid model ID")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip() or not all(character.isprintable() for character in value):
            raise ValueError("Invalid model name")
        return value


class AvailableModelsResponse(ApiModel):
    provider: Literal["bedrock", "anthropic"]
    models: list[AvailableModel] = Field(max_length=1000)
    source: Literal["provider", "catalog"]


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
    forwarded = _provider_key_payload(payload)
    model = payload.get("modelId")
    if not isinstance(model, str) or not model.strip() or len(model.strip()) > 512 or any(
        char.isspace() or not char.isprintable() for char in model.strip()
    ):
        raise HTTPException(status_code=400, detail="Provide a valid model ID without whitespace.")
    forwarded["modelId"] = model.strip()
    result = await run_in_threadpool(_runtime_settings_request, "/settings/llm", "PUT", forwarded)
    response.headers["Cache-Control"] = "no-store"
    return result


@router.post("/llm/models", response_model=AvailableModelsResponse)
async def list_llm_models(request: Request, response: Response) -> AvailableModelsResponse:
    forwarded = _provider_key_payload(await _read_settings_body(request))
    result = await run_in_threadpool(
        _runtime_response, "/settings/llm/models", "POST", forwarded, AvailableModelsResponse,
    )
    if result.provider != forwarded["provider"]:
        raise HTTPException(status_code=502, detail="The runtime returned an invalid model list.")
    response.headers["Cache-Control"] = "no-store"
    return result


def _provider_key_payload(payload) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("provider"), str) or payload["provider"] not in {"bedrock", "anthropic"}:
        raise HTTPException(status_code=400, detail="Select the Bedrock or Anthropic provider.")
    forwarded = {"provider": payload["provider"]}
    key = payload.get("apiKey")
    if key is not None:
        if not isinstance(key, str):
            raise HTTPException(status_code=400, detail="Provide a valid API key or leave it blank to keep the current key.")
        key = key.strip()
        if len(key) > 16384 or any(char.isspace() or not char.isprintable() for char in key):
            raise HTTPException(status_code=400, detail="Provide an API key without whitespace.")
        if key:
            forwarded["apiKey"] = key
    return forwarded


async def _read_settings_body(request: Request):
    # Keep submitted credentials out of validation errors, including bad JSON.
    body = await request.body()
    try:
        return json.loads(body) if len(body) <= 20 * 1024 else None
    except (ValueError, UnicodeDecodeError):
        return None


def _runtime_settings_request(path: str, method: str, payload: dict | None = None) -> RuntimeSettingsResponse:
    llm = _runtime_response(path, method, payload, LlmRuntimeStatus)
    settings = get_settings()
    return RuntimeSettingsResponse(
        mode=settings.runtime_mode,
        runtime_url=settings.ai_runtime_url,
        reachable=True,
        ready=llm.ready,
        llm=llm,
        error=None if llm.ready else "Agent runtime is reachable, but live LLM is not ready.",
    )


def _runtime_response(
    path: str, method: str, payload: dict | None, response_type: type[RuntimeResponseModel],
) -> RuntimeResponseModel:
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
            return response_type.model_validate_json(runtime_response.read())
    except HTTPError as exc:
        exc.close()
        if exc.code in {401, 403}:
            raise HTTPException(
                status_code=503,
                detail="The runtime refused the update. Check AI_SERVICE_SECRET on the API and runtime.",
            ) from None
        if exc.code in {400, 422}:
            if path == "/settings/llm/models":
                raise HTTPException(status_code=400, detail="Could not list models. Check the selected provider and API key.") from None
            raise HTTPException(status_code=400, detail="The runtime rejected the LLM settings. Check the provider, model and API key.") from None
        if path == "/settings/llm/models":
            if exc.code == 429:
                raise HTTPException(status_code=503, detail="Model listing is temporarily rate limited. Try again shortly.") from None
            if exc.code == 504:
                raise HTTPException(status_code=504, detail="The model listing timed out. Try again shortly.") from None
            raise HTTPException(status_code=502, detail="Could not load models from the provider. Check the API key and try again.") from None
        raise HTTPException(status_code=502, detail="The runtime could not apply the LLM settings.") from None
    except (URLError, OSError, TimeoutError):
        raise HTTPException(status_code=503, detail="The agent runtime is unavailable. Try again when it is running.") from None
    except (ValidationError, ValueError, UnicodeDecodeError):
        if path == "/settings/llm/models":
            raise HTTPException(status_code=502, detail="The runtime returned an invalid model list.") from None
        raise HTTPException(status_code=502, detail="The runtime returned an invalid settings response.") from None
