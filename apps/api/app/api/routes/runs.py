from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import verify_ai_service_secret
from app.db import get_db_session
from app.schemas.api import CompleteRunRequest
from app.schemas.domain import Run
from app.schemas.enums import ProcessingEventType, ProcessingStatus, RunStatus
from app.services.events import EventService
from app.services.runs import RunService

router = APIRouter()


@router.patch(
    "/{run_id}",
    response_model=Run,
    dependencies=[Depends(verify_ai_service_secret)],
)
def complete_run(
    run_id: UUID,
    request: CompleteRunRequest,
    db: Session = Depends(get_db_session),
) -> Run:
    run_service = RunService(db)
    existing_run = run_service.get_run(run_id)
    if existing_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    updated_run = run_service.complete_run(
        run_id,
        status=request.status,
        external_run_id=request.external_run_id,
        trace_id=request.trace_id,
        finished_at=request.finished_at,
        total_duration_ms=request.total_duration_ms,
        human_review_required=request.human_review_required,
        final_outcome=request.final_outcome,
        summary=request.summary,
    )
    if updated_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    event_type, event_status = _event_for_run_status(updated_run.status)
    EventService(db).record_event(
        conversation_id=updated_run.conversation_id,
        message_id=updated_run.message_id,
        event_type=event_type,
        actor_name="ai_runtime",
        correlation_id=updated_run.correlation_id,
        status=event_status,
        duration_ms=updated_run.total_duration_ms,
        payload={
            "source": "ai_service",
            "runId": str(updated_run.id),
            "externalRunId": updated_run.external_run_id,
            "traceId": updated_run.trace_id,
            "finalOutcome": updated_run.final_outcome,
            "summary": updated_run.summary.model_dump(
                by_alias=True,
                mode="json",
                exclude_none=True,
            ),
        },
    )

    return updated_run


def _event_for_run_status(
    status: RunStatus,
) -> tuple[ProcessingEventType, ProcessingStatus]:
    if status == RunStatus.FAILED:
        return ProcessingEventType.ACTOR_FAILED, ProcessingStatus.FAILED
    if status == RunStatus.HUMAN_REVIEW_REQUIRED:
        return ProcessingEventType.REVIEW_REQUIRED, ProcessingStatus.HUMAN_REVIEW_REQUIRED
    if status == RunStatus.CANCELLED:
        return ProcessingEventType.ACTOR_FAILED, ProcessingStatus.FAILED
    return ProcessingEventType.PROCESSING_COMPLETED, ProcessingStatus.COMPLETED
