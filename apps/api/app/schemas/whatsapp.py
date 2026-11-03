"""A reviewed capture, never WhatsApp credentials or a background account scrape."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.domain import ApiModel
from app.schemas.enums import ArchitectureMode, RuntimeMode


class WhatsAppCapturedMessage(ApiModel):
    source_id: str = Field(min_length=1, max_length=300)
    role: Literal["customer", "attendant"]
    text: str = Field(min_length=1, max_length=8000)
    timestamp: datetime | None = None

    @field_validator("source_id", "text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message identifier and text must not be blank")
        return value

    @field_validator("timestamp")
    @classmethod
    def timestamp_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("Timestamp must include a timezone")
        return value


class WhatsAppImportRequest(ApiModel):
    source: Literal["whatsapp_web"] = "whatsapp_web"
    capture_id: UUID
    chat_title: str | None = Field(default=None, max_length=200)
    target_source_id: str = Field(min_length=1, max_length=300)
    messages: list[WhatsAppCapturedMessage] = Field(min_length=1, max_length=200)
    architecture_mode: ArchitectureMode = ArchitectureMode.CENTRALIZED_ORCHESTRATION
    runtime_mode: RuntimeMode = RuntimeMode.REAL

    @model_validator(mode="after")
    def valid_prefix(self):
        ids = [m.source_id for m in self.messages]
        if len(set(ids)) != len(ids):
            raise ValueError("Message sourceId values must be unique")
        if self.target_source_id not in ids:
            raise ValueError("targetSourceId must identify a captured message")
        target = ids.index(self.target_source_id)
        if self.messages[target].role != "customer":
            raise ValueError("The target must be a customer message")
        if sum(len(m.text) for m in self.messages) > 64000:
            raise ValueError("Capture exceeds the 64000 character limit")
        return self

    def prefix(self) -> list[WhatsAppCapturedMessage]:
        target = next(i for i, m in enumerate(self.messages) if m.source_id == self.target_source_id)
        return self.messages[:target + 1]


class WhatsAppImportResponse(ApiModel):
    conversation_id: UUID
    message_id: UUID
    run_id: UUID
    run_ids: list[UUID]
    imported_message_count: int
    reused: bool
