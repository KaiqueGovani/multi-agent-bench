"""create runs table

Revision ID: 20260423_0002
Revises: 20260422_0001
Create Date: 2026-04-23 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260423_0002"
down_revision: str | None = "20260422_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_run_id", sa.String(length=160), nullable=True),
        sa.Column("ai_session_id", sa.String(length=500), nullable=True),
        sa.Column("trace_id", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_duration_ms", sa.Integer(), nullable=True),
        sa.Column("human_review_required", sa.Boolean(), nullable=True),
        sa.Column("final_outcome", sa.String(length=120), nullable=True),
        sa.Column("experiment_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_runs_conversation_id_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            name=op.f("fk_runs_message_id_messages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_runs")),
    )
    op.create_index(op.f("ix_runs_ai_session_id"), "runs", ["ai_session_id"], unique=False)
    op.create_index(op.f("ix_runs_conversation_id"), "runs", ["conversation_id"], unique=False)
    op.create_index("ix_runs_conversation_created", "runs", ["conversation_id", "created_at"], unique=False)
    op.create_index(op.f("ix_runs_correlation_id"), "runs", ["correlation_id"], unique=False)
    op.create_index(op.f("ix_runs_external_run_id"), "runs", ["external_run_id"], unique=False)
    op.create_index(op.f("ix_runs_final_outcome"), "runs", ["final_outcome"], unique=False)
    op.create_index(op.f("ix_runs_message_id"), "runs", ["message_id"], unique=False)
    op.create_index("ix_runs_message_created", "runs", ["message_id", "created_at"], unique=False)
    op.create_index(op.f("ix_runs_status"), "runs", ["status"], unique=False)
    op.create_index(op.f("ix_runs_trace_id"), "runs", ["trace_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_runs_trace_id"), table_name="runs")
    op.drop_index(op.f("ix_runs_status"), table_name="runs")
    op.drop_index("ix_runs_message_created", table_name="runs")
    op.drop_index(op.f("ix_runs_message_id"), table_name="runs")
    op.drop_index(op.f("ix_runs_final_outcome"), table_name="runs")
    op.drop_index(op.f("ix_runs_external_run_id"), table_name="runs")
    op.drop_index(op.f("ix_runs_correlation_id"), table_name="runs")
    op.drop_index("ix_runs_conversation_created", table_name="runs")
    op.drop_index(op.f("ix_runs_conversation_id"), table_name="runs")
    op.drop_index(op.f("ix_runs_ai_session_id"), table_name="runs")
    op.drop_table("runs")
