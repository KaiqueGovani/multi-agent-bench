from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.schemas.api import ResolveReviewTaskRequest, ReviewTaskListResponse
from app.schemas.domain import ReviewTask
from app.services.reviews import ReviewService, ReviewValidationError

router = APIRouter()


@router.get("", response_model=ReviewTaskListResponse)
def list_open_reviews(db: Session = Depends(get_db_session)) -> ReviewTaskListResponse:
    return ReviewTaskListResponse(review_tasks=ReviewService(db).list_open_review_tasks())


@router.patch("/{review_task_id}/resolve", response_model=ReviewTask)
def resolve_review_task(
    review_task_id: UUID,
    request: ResolveReviewTaskRequest,
    db: Session = Depends(get_db_session),
) -> ReviewTask:
    try:
        review_task = ReviewService(db).resolve_review_task(
            review_task_id,
            status=request.status,
            note=request.note,
            resolved_by=request.resolved_by,
        )
    except ReviewValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if review_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review task not found",
        )
    return review_task
