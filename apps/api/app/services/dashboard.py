from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AttachmentModel,
    ConversationModel,
    MessageModel,
    ProcessingEventModel,
    ReviewTaskModel,
    RunExecutionEventModel,
    RunModel,
)
from app.schemas.api import (
    DashboardConversationItem,
    DashboardDistributionItem,
    DashboardMetricsResponse,
    DashboardTotals,
)
from app.schemas.enums import ConversationStatus, ReviewTaskStatus, RunStatus


class DashboardService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_metrics(self) -> DashboardMetricsResponse:
        runs = list(self._db.scalars(select(RunModel)).all())
        attachments = list(self._db.scalars(select(AttachmentModel)).all())
        execution_events = list(self._db.scalars(select(RunExecutionEventModel)).all())
        return DashboardMetricsResponse(
            generated_at=datetime.now(UTC),
            totals=self._totals(runs),
            by_architecture=self._run_distribution(runs, "architectureKey"),
            by_model=self._run_distribution(runs, "modelName"),
            by_scenario=self._run_distribution(runs, "scenarioId"),
            by_attachment_type=self._attachment_distribution(attachments),
            by_tool=self._tool_distribution(execution_events),
            latency_percentiles=self._latency_percentiles(runs),
            conversations=self._conversation_items(),
        )

    def _totals(self, runs: list[RunModel]) -> DashboardTotals:
        durations = [
            run.total_duration_ms
            for run in runs
            if isinstance(run.total_duration_ms, int)
        ]
        return DashboardTotals(
            conversations=self._count(ConversationModel),
            runs=len(runs),
            runs_completed=sum(1 for run in runs if run.status == RunStatus.COMPLETED.value),
            runs_failed=sum(1 for run in runs if run.status == RunStatus.FAILED.value),
            runs_human_review=sum(
                1
                for run in runs
                if run.status == RunStatus.HUMAN_REVIEW_REQUIRED.value
                or run.human_review_required is True
            ),
            messages=self._count(MessageModel),
            attachments=self._count(AttachmentModel),
            events=self._count(ProcessingEventModel),
            average_run_duration_ms=(
                round(sum(durations) / len(durations)) if durations else None
            ),
        )

    def _run_distribution(
        self,
        runs: list[RunModel],
        metadata_key: str,
    ) -> list[DashboardDistributionItem]:
        counts: dict[str, int] = defaultdict(int)
        durations_by_key: dict[str, list[int]] = defaultdict(list)
        for run in runs:
            key = str((run.experiment_json or {}).get(metadata_key) or "unknown")
            counts[key] += 1
            if isinstance(run.total_duration_ms, int):
                durations_by_key[key].append(run.total_duration_ms)

        return [
            DashboardDistributionItem(
                key=key,
                count=count,
                average_run_duration_ms=(
                    round(sum(durations) / len(durations)) if durations else None
                ),
            )
            for key, count in sorted(
                counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
            for durations in [durations_by_key[key]]
        ]

    def _attachment_distribution(
        self,
        attachments: list[AttachmentModel],
    ) -> list[DashboardDistributionItem]:
        counts: dict[str, int] = defaultdict(int)
        for attachment in attachments:
            counts[attachment.mime_type] += 1
        return [
            DashboardDistributionItem(key=key, count=count)
            for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ]

    def _tool_distribution(
        self,
        execution_events: list[RunExecutionEventModel],
    ) -> list[DashboardDistributionItem]:
        counts: dict[str, int] = defaultdict(int)
        for event in execution_events:
            if event.event_family != "tool":
                continue
            key = event.tool_name or "unknown"
            counts[key] += 1
        return [
            DashboardDistributionItem(key=key, count=count)
            for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ]

    def _latency_percentiles(self, runs: list[RunModel]) -> dict[str, int]:
        durations = sorted(
            run.total_duration_ms
            for run in runs
            if isinstance(run.total_duration_ms, int)
        )
        if not durations:
            return {}

        def pick(percentile: float) -> int:
            index = min(len(durations) - 1, max(0, round((len(durations) - 1) * percentile)))
            return int(durations[index])

        return {
            "p50": pick(0.50),
            "p90": pick(0.90),
            "p95": pick(0.95),
        }

    def _conversation_items(self, *, limit: int = 8) -> list[DashboardConversationItem]:
        conversations = self._db.scalars(
            select(ConversationModel)
            .order_by(ConversationModel.updated_at.desc(), ConversationModel.created_at.desc())
            .limit(limit)
        ).all()
        return [self._conversation_item(conversation) for conversation in conversations]

    def _conversation_item(self, conversation: ConversationModel) -> DashboardConversationItem:
        latest_run = self._db.scalars(
            select(RunModel)
            .where(RunModel.conversation_id == conversation.id)
            .order_by(RunModel.created_at.desc(), RunModel.id.desc())
            .limit(1)
        ).first()
        last_message = self._db.scalars(
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation.id)
            .order_by(MessageModel.created_at_server.desc(), MessageModel.id.desc())
            .limit(1)
        ).first()
        pending_reviews = self._db.scalar(
            select(func.count())
            .select_from(ReviewTaskModel)
            .where(
                ReviewTaskModel.conversation_id == conversation.id,
                ReviewTaskModel.status.in_(
                    [ReviewTaskStatus.OPEN.value, ReviewTaskStatus.IN_REVIEW.value]
                ),
            )
        )

        return DashboardConversationItem(
            conversation_id=conversation.id,
            status=ConversationStatus(conversation.status),
            updated_at=conversation.updated_at,
            latest_run_id=latest_run.id if latest_run else None,
            last_message=last_message.content_text if last_message else None,
            run_count=self._count_runs(conversation.id),
            review_pending=bool(pending_reviews),
        )

    def _count(self, model: type[ConversationModel] | type[MessageModel] | type[AttachmentModel] | type[ProcessingEventModel]) -> int:
        return int(self._db.scalar(select(func.count()).select_from(model)) or 0)

    def _count_runs(self, conversation_id: UUID) -> int:
        return int(
            self._db.scalar(
                select(func.count())
                .select_from(RunModel)
                .where(RunModel.conversation_id == conversation_id)
            )
            or 0
        )
