from collections.abc import Sequence
from uuid import UUID

from fastapi import UploadFile

from app.core.config import get_settings
from app.domain.channels import ChannelAttachment, ChannelInboundMessage
from app.schemas.domain import OperationalMetadata
from app.schemas.enums import ChannelType


class WebChatAdapter:
    channel = ChannelType.WEB_CHAT

    async def normalize_inbound_message(
        self,
        *,
        conversation_id: UUID,
        text: str | None,
        metadata: OperationalMetadata,
        client_message_id: str | None = None,
        files: Sequence[UploadFile] | None = None,
    ) -> ChannelInboundMessage:
        settings = get_settings()
        channel_metadata = metadata.model_copy(
            update={
                "channel": self.channel,
                "architecture_mode": (
                    metadata.architecture_mode or settings.default_architecture_mode
                ),
                "file_count": len(files or []),
                "runtime_mode": metadata.runtime_mode or settings.runtime_mode,
            }
        )
        attachments = [
            ChannelAttachment(
                original_filename=file.filename or "attachment",
                mime_type=file.content_type or "application/octet-stream",
                content=await file.read(),
            )
            for file in (files or [])
        ]

        return ChannelInboundMessage(
            channel=self.channel,
            conversation_id=conversation_id,
            text=text,
            attachments=attachments,
            client_message_id=client_message_id,
            created_at_client=channel_metadata.client_timestamp,
            metadata=channel_metadata,
        )
