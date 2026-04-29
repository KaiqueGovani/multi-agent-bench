import logging

from app.core.config import Settings


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(message)s",
    )


def configure_telemetry(settings: Settings) -> None:
    if not settings.enable_otel:
        return
    try:
        from strands.telemetry import StrandsTelemetry  # type: ignore

        StrandsTelemetry().setup_otlp_exporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
            service_name=settings.otel_service_name,
        )
    except Exception:  # pragma: no cover - optional integration
        logging.getLogger("agent_runtime.telemetry").warning(
            "Failed to initialize Strands OTEL exporter; continuing without OTEL",
        )
