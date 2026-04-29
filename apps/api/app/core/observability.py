import json
import logging
import time
from contextvars import ContextVar
from uuid import UUID, uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


request_id_context: ContextVar[UUID | None] = ContextVar(
    "request_id",
    default=None,
)


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(message)s",
    )


def get_request_id(request: Request) -> UUID:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, UUID):
        return request_id
    return uuid4()


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, logger_name: str = "app.requests") -> None:
        super().__init__(app)
        self._logger = logging.getLogger(logger_name)

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = _resolve_request_id(request)
        request.state.request_id = request_id
        token = request_id_context.set(request_id)
        started_at = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = _duration_ms(started_at)
            self._logger.exception(
                _as_json(
                    {
                        "event": "http.request.failed",
                        "requestId": str(request_id),
                        "method": request.method,
                        "path": request.url.path,
                        "durationMs": duration_ms,
                    }
                )
            )
            raise
        finally:
            request_id_context.reset(token)

        duration_ms = _duration_ms(started_at)
        response.headers["X-Request-ID"] = str(request_id)
        self._logger.info(
            _as_json(
                {
                    "event": "http.request.completed",
                    "requestId": str(request_id),
                    "method": request.method,
                    "path": request.url.path,
                    "statusCode": response.status_code,
                    "durationMs": duration_ms,
                }
            )
        )
        return response


def _resolve_request_id(request: Request) -> UUID:
    header_value = request.headers.get("x-request-id")
    if header_value:
        try:
            return UUID(header_value)
        except ValueError:
            return uuid4()
    return uuid4()


def _duration_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)


def _as_json(payload: dict) -> str:
    return json.dumps(payload, separators=(",", ":"))
