from collections.abc import Mapping
from typing import Any

from app.domain.channels import ChannelInboundMessage
from app.schemas.enums import ChannelType
from app.schemas.domain import OperationalMetadata
from app.schemas.whatsapp import WhatsAppCapturedMessage


class WhatsAppAdapter:
    channel = ChannelType.WHATSAPP

    async def normalize_inbound_message(
        self,
        *,
        payload: Mapping[str, Any],
    ) -> ChannelInboundMessage:
        message = WhatsAppCapturedMessage.model_validate(payload)
        return ChannelInboundMessage(
            channel=self.channel,
            conversation_id=None,
            text=message.text,
            client_message_id=message.source_id,
            created_at_client=message.timestamp,
            metadata=OperationalMetadata.model_validate({
                "channel": "whatsapp", "source": "whatsapp_web",
                "sourceMessageId": message.source_id,
                "importedHistory": True, "sourceRole": message.role,
            }),
        )
