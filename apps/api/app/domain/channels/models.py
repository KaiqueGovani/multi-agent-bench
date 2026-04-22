from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.schemas.domain import ModelContext, OperationalMetadata
from app.schemas.enums import ChannelType


@dataclass(frozen=True)
class ChannelAttachment:
    original_filename: str
    mime_type: str
    content: bytes
    client_attachment_id: str | None = None
    metadata: OperationalMetadata = field(default_factory=OperationalMetadata)

    @property
    def size_bytes(self) -> int:
        return len(self.content)


@dataclass(frozen=True)
class ChannelInboundMessage:
    channel: ChannelType
    conversation_id: UUID | None
    text: str | None = None
    attachments: list[ChannelAttachment] = field(default_factory=list)
    client_message_id: str | None = None
    user_session_id: str | None = None
    created_at_client: datetime | None = None
    metadata: OperationalMetadata = field(default_factory=OperationalMetadata)
    model_context: ModelContext | None = None
