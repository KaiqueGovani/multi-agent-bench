from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import replace
from ipaddress import ip_address
import json
import logging
import secrets
from threading import Lock

from fastapi import FastAPI, HTTPException, Request, Response, status

from app.architectures.base import Agent, BedrockModel
from app.core.config import Settings, get_settings
from app.core.models import AnthropicModel, get_api_key, get_model_id
from app.schemas.runtime import HealthResponse, LlmModelListResponse, LlmRuntimeStatus, RuntimeDispatchRequest, RuntimeDispatchResponse
from app.services.execution import RuntimeExecutionService
from app.services.model_discovery import discover_models, ModelDiscoveryError
from app.telemetry.setup import configure_logging, configure_telemetry

logger = logging.getLogger(__name__)

# Thread pool for parallel run execution within a single worker.
# Keep a single HTTP worker when using the in-memory credential update endpoint.
# Live inference itself runs in isolated child processes.
_executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="runtime-run-")


def _log_failed_future(future: Future[object]) -> None:
    try:
        future.result()
    except Exception:
        logger.exception("Runtime worker failed after request acceptance")


def create_app() -> FastAPI:
    settings = get_settings()
    settings_lock = Lock()
    configure_logging(settings.log_level)
    configure_telemetry(settings)
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    def current_settings() -> Settings:
        with settings_lock:
            return settings

    def llm_status(snapshot: Settings) -> LlmRuntimeStatus:
        token_configured = bool(get_api_key(snapshot))
        provider_model = AnthropicModel if snapshot.model_provider == "anthropic" else BedrockModel
        sdk_available = Agent is not None and provider_model is not None
        return LlmRuntimeStatus(
            provider=snapshot.model_provider,
            models={"bedrock": snapshot.bedrock_model_id, "anthropic": snapshot.anthropic_model_id},
            credentials_configured={"bedrock": bool(snapshot.aws_bearer_token_bedrock),
                                    "anthropic": bool(snapshot.anthropic_api_key)},
            enabled=snapshot.enable_live_llm,
            token_configured=token_configured,
            sdk_available=sdk_available,
            ready=snapshot.enable_live_llm and token_configured and sdk_available,
            model_id=get_model_id(snapshot),
            region=snapshot.aws_region,
        )

    @application.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        snapshot = current_settings()
        return HealthResponse(
            status="ok",
            service=snapshot.app_name,
            version=snapshot.app_version,
            environment=snapshot.environment,
            llm=llm_status(snapshot),
        )

    def authorize_settings(request: Request) -> None:
        snapshot = current_settings()
        if snapshot.ai_service_secret:
            provided = request.headers.get("X-AI-Service-Secret", "")
            authorized = secrets.compare_digest(provided.encode(), snapshot.ai_service_secret.encode())
        else:
            try:
                authorized = bool(request.client and ip_address(request.client.host).is_loopback)
            except ValueError:
                authorized = False
            authorized = authorized and "origin" not in request.headers
        if not authorized:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Runtime settings access denied.")

    async def read_settings_payload(request: Request, detail: str) -> dict:
        # Parse explicitly so validation errors never include the submitted secret.
        try:
            payload = json.loads(await request.body())
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from None
        if not isinstance(payload, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        return payload

    def valid_value(value: object, *, maximum: int) -> bool:
        return bool(isinstance(value, str) and value and len(value) <= maximum
                    and all(not character.isspace() and character.isprintable() for character in value))

    @application.put("/settings/bedrock", response_model=LlmRuntimeStatus)
    async def update_bedrock_key(request: Request, response: Response) -> LlmRuntimeStatus:
        nonlocal settings
        authorize_settings(request)
        payload = await read_settings_payload(request, "A valid Bedrock API key is required.")
        key = payload.get("apiKey")
        if isinstance(key, str):
            key = key.strip()
        if not valid_value(key, maximum=16384):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A valid Bedrock API key is required.")

        with settings_lock:
            settings = replace(settings, aws_bearer_token_bedrock=key)
            snapshot = settings
        response.headers["Cache-Control"] = "no-store"
        return llm_status(snapshot)

    @application.get("/settings/llm", response_model=LlmRuntimeStatus)
    def get_llm_settings(request: Request, response: Response) -> LlmRuntimeStatus:
        authorize_settings(request)
        response.headers["Cache-Control"] = "no-store"
        return llm_status(current_settings())

    @application.put("/settings/llm", response_model=LlmRuntimeStatus)
    async def update_llm_settings(request: Request, response: Response) -> LlmRuntimeStatus:
        nonlocal settings
        authorize_settings(request)
        detail = "Valid provider, model ID and API key settings are required."
        payload = await read_settings_payload(request, detail)
        provider, model_id = payload.get("provider"), payload.get("modelId")
        if isinstance(model_id, str):
            model_id = model_id.strip()
        key = payload.get("apiKey", "")
        if isinstance(key, str):
            key = key.strip()
        if (not isinstance(provider, str) or provider not in {"bedrock", "anthropic"}
            or not valid_value(model_id, maximum=512)
            or not isinstance(key, str)
            or (key and not valid_value(key, maximum=16384))):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

        with settings_lock:
            credential_name = "anthropic_api_key" if provider == "anthropic" else "aws_bearer_token_bedrock"
            model_name = "anthropic_model_id" if provider == "anthropic" else "bedrock_model_id"
            credential = key or getattr(settings, credential_name)
            if not credential:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail="An API key is required for the selected provider.")
            settings = replace(settings, model_provider=provider,
                               **{credential_name: credential, model_name: model_id})
            snapshot = settings
        response.headers["Cache-Control"] = "no-store"
        return llm_status(snapshot)

    @application.post("/settings/llm/models", response_model=LlmModelListResponse)
    async def list_llm_models(request: Request, response: Response) -> LlmModelListResponse:
        authorize_settings(request)
        detail = "A valid provider and API key are required."
        payload = await read_settings_payload(request, detail)
        provider, key = payload.get("provider"), payload.get("apiKey", "")
        if isinstance(key, str):
            key = key.strip()
        if (not isinstance(provider, str) or provider not in {"bedrock", "anthropic"}
            or not isinstance(key, str) or (key and not valid_value(key, maximum=16384))):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        snapshot = current_settings()
        retained_key = snapshot.anthropic_api_key if provider == "anthropic" else snapshot.aws_bearer_token_bedrock
        try:
            listing = await discover_models(provider, key or retained_key, snapshot)
        except ModelDiscoveryError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
        response.headers["Cache-Control"] = "no-store"
        return listing

    @application.post("/runs", response_model=RuntimeDispatchResponse, status_code=status.HTTP_202_ACCEPTED)
    def create_run(
        request: RuntimeDispatchRequest,
    ) -> RuntimeDispatchResponse:
        snapshot = current_settings()
        if snapshot.enable_live_llm and not get_api_key(snapshot):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=("ANTHROPIC_API_KEY" if snapshot.model_provider == "anthropic" else "AWS_BEARER_TOKEN_BEDROCK")
                       + " is required when ENABLE_LIVE_LLM=true",
            )
        request = request.model_copy(update={"experiment": request.experiment.model_copy(update={
            "model_provider": snapshot.model_provider, "model_name": get_model_id(snapshot),
        })})
        # Submit to thread pool for parallel execution
        future = _executor.submit(RuntimeExecutionService(snapshot, isolate_live=True).execute_run, request)
        future.add_done_callback(_log_failed_future)
        return RuntimeDispatchResponse(run_id=request.run_id, model_provider=snapshot.model_provider,
                                       model_name=get_model_id(snapshot))

    return application


app = create_app()
