from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.schemas.api import DashboardMetricsResponse
from app.services.dashboard import DashboardService

router = APIRouter()


@router.get("/dashboard/metrics", response_model=DashboardMetricsResponse)
def get_dashboard_metrics(
    db: Session = Depends(get_db_session),
) -> DashboardMetricsResponse:
    return DashboardService(db).get_metrics()
