"""create initial tables

Revision ID: 20260422_0001
Revises:
Create Date: 2026-04-22 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260422_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("user_session_id", sa.String(length=120), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversations")),
    )
    op.create_index(op.f("ix_conversations_channel"), "conversations", ["channel"], unique=False)
    op.create_index(op.f("ix_conversations_status"), "conversations", ["status"], unique=False)
    op.create_index(op.f("ix_conversations_user_session_id"), "conversations", ["user_session_id"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("created_at_client", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at_server", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_context_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_messages_conversation_id_conversations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
    )
    op.create_index(op.f("ix_messages_conversation_id"), "messages", ["conversation_id"], unique=False)
    op.create_index("ix_messages_conversation_created", "messages", ["conversation_id", "created_at_server"], unique=False)
    op.create_index(op.f("ix_messages_correlation_id"), "messages", ["correlation_id"], unique=False)
    op.create_index(op.f("ix_messages_direction"), "messages", ["direction"], unique=False)
    op.create_index(op.f("ix_messages_status"), "messages", ["status"], unique=False)

    op.create_table(
        "attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=160), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            name=op.f("fk_attachments_message_id_messages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attachments")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_attachments_storage_key")),
    )
    op.create_index(op.f("ix_attachments_checksum"), "attachments", ["checksum"], unique=False)
    op.create_index(op.f("ix_attachments_message_id"), "attachments", ["message_id"], unique=False)
    op.create_index(op.f("ix_attachments_mime_type"), "attachments", ["mime_type"], unique=False)
    op.create_index(op.f("ix_attachments_status"), "attachments", ["status"], unique=False)

    op.create_table(
        "processing_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("actor_name", sa.String(length=120), nullable=True),
        sa.Column("parent_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_processing_events_conversation_id_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            name=op.f("fk_processing_events_message_id_messages"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["parent_event_id"],
            ["processing_events.id"],
            name=op.f("fk_processing_events_parent_event_id_processing_events"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_processing_events")),
    )
    op.create_index(op.f("ix_processing_events_actor_name"), "processing_events", ["actor_name"], unique=False)
    op.create_index("ix_processing_events_conversation_created", "processing_events", ["conversation_id", "created_at"], unique=False)
    op.create_index(op.f("ix_processing_events_conversation_id"), "processing_events", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_processing_events_correlation_id"), "processing_events", ["correlation_id"], unique=False)
    op.create_index(op.f("ix_processing_events_event_type"), "processing_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_processing_events_message_id"), "processing_events", ["message_id"], unique=False)
    op.create_index(op.f("ix_processing_events_status"), "processing_events", ["status"], unique=False)

    op.create_table(
        "review_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_review_tasks_conversation_id_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            name=op.f("fk_review_tasks_message_id_messages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_tasks")),
    )
    op.create_index(op.f("ix_review_tasks_conversation_id"), "review_tasks", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_review_tasks_message_id"), "review_tasks", ["message_id"], unique=False)
    op.create_index(op.f("ix_review_tasks_status"), "review_tasks", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_review_tasks_status"), table_name="review_tasks")
    op.drop_index(op.f("ix_review_tasks_message_id"), table_name="review_tasks")
    op.drop_index(op.f("ix_review_tasks_conversation_id"), table_name="review_tasks")
    op.drop_table("review_tasks")

    op.drop_index(op.f("ix_processing_events_status"), table_name="processing_events")
    op.drop_index(op.f("ix_processing_events_message_id"), table_name="processing_events")
    op.drop_index(op.f("ix_processing_events_event_type"), table_name="processing_events")
    op.drop_index(op.f("ix_processing_events_correlation_id"), table_name="processing_events")
    op.drop_index(op.f("ix_processing_events_conversation_id"), table_name="processing_events")
    op.drop_index("ix_processing_events_conversation_created", table_name="processing_events")
    op.drop_index(op.f("ix_processing_events_actor_name"), table_name="processing_events")
    op.drop_table("processing_events")

    op.drop_index(op.f("ix_attachments_status"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_mime_type"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_message_id"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_checksum"), table_name="attachments")
    op.drop_table("attachments")

    op.drop_index(op.f("ix_messages_status"), table_name="messages")
    op.drop_index(op.f("ix_messages_direction"), table_name="messages")
    op.drop_index(op.f("ix_messages_correlation_id"), table_name="messages")
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages")
    op.drop_table("messages")

    op.drop_index(op.f("ix_conversations_user_session_id"), table_name="conversations")
    op.drop_index(op.f("ix_conversations_status"), table_name="conversations")
    op.drop_index(op.f("ix_conversations_channel"), table_name="conversations")
    op.drop_table("conversations")

