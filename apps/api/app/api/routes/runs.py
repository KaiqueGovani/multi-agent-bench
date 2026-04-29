import asyncio
from queue import Empty
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.security import verify_ai_service_secret
from app.db import get_db_session
from app.schemas.api import CompleteRunRequest, RunComparisonContextResponse, RunExecutionResponse
from app.schemas.domain import Run
from app.schemas.enums import ProcessingEventType, ProcessingStatus, RunStatus
from app.services.dashboard import DashboardService
from app.services.events import EventService
from app.services.event_bus import run_execution_bus
from app.services.run_execution import RunExecutionService
from app.services.runs import RunService

router = APIRouter()


@router.get("/{run_id}", response_model=Run)
def get_run(
    run_id: UUID,
    db: Session = Depends(get_db_session),
) -> Run:
    run = RunService(db).get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.get("/{run_id}/execution", response_model=RunExecutionResponse)
def get_run_execution(
    run_id: UUID,
    db: Session = Depends(get_db_session),
) -> RunExecutionResponse:
    run_service = RunService(db)
    run = run_service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    execution_service = RunExecutionService(db)
    return RunExecutionResponse(
        run=run,
        projection=execution_service.get_run_execution_projection(run_id),
        execution_events=execution_service.list_run_execution_events(run_id),
    )


@router.get("/{run_id}/comparison-context", response_model=RunComparisonContextResponse)
def get_run_comparison_context(
    run_id: UUID,
    db: Session = Depends(get_db_session),
) -> RunComparisonContextResponse:
    run_service = RunService(db)
    run = run_service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    metrics = DashboardService(db).get_metrics()
    return RunComparisonContextResponse(
        run=run,
        peer_runs=run_service.list_related_runs(run_id),
        architecture_distribution=metrics.by_architecture,
        scenario_distribution=metrics.by_scenario,
    )


@router.get("/{run_id}/execution/stream")
async def stream_run_execution(
    run_id: UUID,
    request: Request,
    last_sequence_no: int = Query(default=0, alias="lastSequenceNo"),
    db: Session = Depends(get_db_session),
) -> EventSourceResponse:
    run = RunService(db).get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    execution_service = RunExecutionService(db)
    subscriber = run_execution_bus.subscribe(run_id)

    async def event_generator():
        try:
            for event in execution_service.list_run_execution_events(run_id):
                if event.sequence_no <= last_sequence_no:
                    continue
                yield {
                    "event": "run.execution",
                    "id": str(event.id),
                    "data": event.model_dump_json(by_alias=True),
                    "retry": 2000,
                }

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.to_thread(subscriber.queue.get, True, 15)
                except Empty:
                    yield {
                        "event": "heartbeat",
                        "data": "{}",
                        "retry": 2000,
                    }
                    continue
                yield {
                    "event": "run.execution",
                    "id": str(event.id),
                    "data": event.model_dump_json(by_alias=True),
                    "retry": 2000,
                }
        finally:
            run_execution_bus.unsubscribe(run_id, subscriber)

    return EventSourceResponse(event_generator())


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
