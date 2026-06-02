from concurrent.futures import Future, ThreadPoolExecutor
import logging
from fastapi import FastAPI, HTTPException, status

from app.architectures.base import Agent, BedrockModel
from app.core.config import get_settings
from app.schemas.runtime import HealthResponse, LlmRuntimeStatus, RuntimeDispatchRequest, RuntimeDispatchResponse
from app.services.execution import RuntimeExecutionService
from app.telemetry.setup import configure_logging, configure_telemetry

logger = logging.getLogger(__name__)

# Thread pool for parallel run execution within a single worker.
# For true parallelism with LLM calls, use multiple uvicorn workers: `uvicorn --workers 4`
_executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="runtime-run-")


def _log_failed_future(future: Future[object]) -> None:
    try:
        future.result()
    except Exception:
        logger.exception("Runtime worker failed after request acceptance")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_telemetry(settings)
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @application.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        token_configured = bool(settings.aws_bearer_token_bedrock)
        sdk_available = Agent is not None and BedrockModel is not None
        return HealthResponse(
            status="ok",
            service=settings.app_name,
            version=settings.app_version,
            environment=settings.environment,
            llm=LlmRuntimeStatus(
                enabled=settings.enable_live_llm,
                token_configured=token_configured,
                sdk_available=sdk_available,
                ready=settings.enable_live_llm and token_configured and sdk_available,
                model_id=settings.bedrock_model_id,
                region=settings.aws_region,
            ),
        )

    @application.post("/runs", response_model=RuntimeDispatchResponse, status_code=status.HTTP_202_ACCEPTED)
    def create_run(
        request: RuntimeDispatchRequest,
    ) -> RuntimeDispatchResponse:
        if settings.enable_live_llm and not settings.aws_bearer_token_bedrock:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AWS_BEARER_TOKEN_BEDROCK is required when ENABLE_LIVE_LLM=true",
            )
        # Submit to thread pool for parallel execution
        future = _executor.submit(RuntimeExecutionService(settings).execute_run, request)
        future.add_done_callback(_log_failed_future)
        return RuntimeDispatchResponse(run_id=request.run_id)

    return application


app = create_app()
