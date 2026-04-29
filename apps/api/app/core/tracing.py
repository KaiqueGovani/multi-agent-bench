import secrets
from uuid import UUID


def extract_trace_id(traceparent: str | None) -> str:
    if not traceparent:
        return secrets.token_hex(16)
    parts = traceparent.split("-")
    if len(parts) != 4:
        return secrets.token_hex(16)
    trace_id = parts[1]
    if len(trace_id) != 32 or trace_id == "0" * 32:
        return secrets.token_hex(16)
    try:
        int(trace_id, 16)
    except ValueError:
        return secrets.token_hex(16)
    return trace_id


def build_traceparent(trace_id: str) -> str:
    span_id = secrets.token_hex(8)
    return f"00-{trace_id}-{span_id}-01"


def build_baggage(
    *,
    conversation_id: UUID,
    message_id: UUID,
    run_id: UUID,
    architecture_key: str | None,
    model_key: str | None,
    experiment_id: str | None,
) -> str:
    values = {
        "conversation_id": str(conversation_id),
        "message_id": str(message_id),
        "run_id": str(run_id),
        "architecture_key": architecture_key,
        "model_key": model_key,
        "experiment_id": experiment_id,
    }
    return ",".join(
        f"{key}={_sanitize_baggage_value(value)}"
        for key, value in values.items()
        if value
    )


def _sanitize_baggage_value(value: str) -> str:
    return value.replace(",", "_").replace(";", "_").replace(" ", "_")
