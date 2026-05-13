from concurrent.futures import ThreadPoolExecutor
import logging
from fastapi import FastAPI, HTTPException, status

from app.core.config import get_settings
from app.schemas.runtime import HealthResponse, RuntimeDispatchRequest, RuntimeDispatchResponse
from app.services.execution import RuntimeExecutionService
from app.telemetry.setup import configure_logging, configure_telemetry

logger = logging.getLogger(__name__)

# Thread pool for parallel run execution within a single worker.
# For true parallelism with LLM calls, use multiple uvicorn workers: `uvicorn --workers 4`
_executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="runtime-run-")


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
        return HealthResponse(
            status="ok",
            service=settings.app_name,
            version=settings.app_version,
            environment=settings.environment,
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
        _executor.submit(RuntimeExecutionService(settings).execute_run, request)
        return RuntimeDispatchResponse(run_id=request.run_id)

    return application


app = create_app()
