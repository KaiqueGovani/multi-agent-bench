"""create run execution tables

Revision ID: 20260429_0003
Revises: 20260423_0002
Create Date: 2026-04-29 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260429_0003"
down_revision: str | None = "20260423_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "run_execution_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_family", sa.String(length=40), nullable=False),
        sa.Column("event_name", sa.String(length=120), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("actor_name", sa.String(length=120), nullable=True),
        sa.Column("node_id", sa.String(length=120), nullable=True),
        sa.Column("tool_name", sa.String(length=120), nullable=True),
        sa.Column("source", sa.String(length=60), nullable=True),
        sa.Column("external_event_id", sa.String(length=200), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_run_execution_events_conversation_id_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            name=op.f("fk_run_execution_events_message_id_messages"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.id"],
            name=op.f("fk_run_execution_events_run_id_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_run_execution_events")),
    )
    op.create_index(op.f("ix_run_execution_events_actor_name"), "run_execution_events", ["actor_name"], unique=False)
    op.create_index(op.f("ix_run_execution_events_conversation_id"), "run_execution_events", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_run_execution_events_correlation_id"), "run_execution_events", ["correlation_id"], unique=False)
    op.create_index(op.f("ix_run_execution_events_event_family"), "run_execution_events", ["event_family"], unique=False)
    op.create_index(op.f("ix_run_execution_events_event_name"), "run_execution_events", ["event_name"], unique=False)
    op.create_index(op.f("ix_run_execution_events_external_event_id"), "run_execution_events", ["external_event_id"], unique=False)
    op.create_index(op.f("ix_run_execution_events_message_id"), "run_execution_events", ["message_id"], unique=False)
    op.create_index(op.f("ix_run_execution_events_node_id"), "run_execution_events", ["node_id"], unique=False)
    op.create_index("ix_run_execution_events_run_sequence", "run_execution_events", ["run_id", "sequence_no"], unique=False)
    op.create_index(op.f("ix_run_execution_events_run_id"), "run_execution_events", ["run_id"], unique=False)
    op.create_index(op.f("ix_run_execution_events_source"), "run_execution_events", ["source"], unique=False)
    op.create_index(op.f("ix_run_execution_events_status"), "run_execution_events", ["status"], unique=False)
    op.create_index(op.f("ix_run_execution_events_tool_name"), "run_execution_events", ["tool_name"], unique=False)

    op.create_table(
        "run_execution_projections",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("architecture_mode", sa.String(length=80), nullable=False),
        sa.Column("run_status", sa.String(length=60), nullable=False),
        sa.Column("active_node_id", sa.String(length=120), nullable=True),
        sa.Column("active_actor_name", sa.String(length=120), nullable=True),
        sa.Column("current_phase", sa.String(length=120), nullable=True),
        sa.Column("source", sa.String(length=60), nullable=True),
        sa.Column("architecture_view_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metrics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("state_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_run_execution_projections_conversation_id_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            name=op.f("fk_run_execution_projections_message_id_messages"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.id"],
            name=op.f("fk_run_execution_projections_run_id_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("run_id", name=op.f("pk_run_execution_projections")),
    )
    op.create_index(op.f("ix_run_execution_projections_architecture_mode"), "run_execution_projections", ["architecture_mode"], unique=False)
    op.create_index(op.f("ix_run_execution_projections_conversation_id"), "run_execution_projections", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_run_execution_projections_message_id"), "run_execution_projections", ["message_id"], unique=False)
    op.create_index(op.f("ix_run_execution_projections_run_status"), "run_execution_projections", ["run_status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_run_execution_projections_run_status"), table_name="run_execution_projections")
    op.drop_index(op.f("ix_run_execution_projections_message_id"), table_name="run_execution_projections")
    op.drop_index(op.f("ix_run_execution_projections_conversation_id"), table_name="run_execution_projections")
    op.drop_index(op.f("ix_run_execution_projections_architecture_mode"), table_name="run_execution_projections")
    op.drop_table("run_execution_projections")

    op.drop_index(op.f("ix_run_execution_events_tool_name"), table_name="run_execution_events")
    op.drop_index(op.f("ix_run_execution_events_status"), table_name="run_execution_events")
    op.drop_index(op.f("ix_run_execution_events_source"), table_name="run_execution_events")
    op.drop_index(op.f("ix_run_execution_events_run_id"), table_name="run_execution_events")
    op.drop_index("ix_run_execution_events_run_sequence", table_name="run_execution_events")
    op.drop_index(op.f("ix_run_execution_events_node_id"), table_name="run_execution_events")
    op.drop_index(op.f("ix_run_execution_events_message_id"), table_name="run_execution_events")
    op.drop_index(op.f("ix_run_execution_events_external_event_id"), table_name="run_execution_events")
    op.drop_index(op.f("ix_run_execution_events_event_name"), table_name="run_execution_events")
    op.drop_index(op.f("ix_run_execution_events_event_family"), table_name="run_execution_events")
    op.drop_index(op.f("ix_run_execution_events_correlation_id"), table_name="run_execution_events")
    op.drop_index(op.f("ix_run_execution_events_conversation_id"), table_name="run_execution_events")
    op.drop_index(op.f("ix_run_execution_events_actor_name"), table_name="run_execution_events")
    op.drop_table("run_execution_events")
