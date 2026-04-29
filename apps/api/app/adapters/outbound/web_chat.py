from collections.abc import Mapping
from typing import Any

from app.schemas.domain import NormalizedOutboundMessage
from app.schemas.enums import ChannelType


class WebChatOutboundAdapter:
    channel = ChannelType.WEB_CHAT

    def format_outbound_message(
        self,
        message: NormalizedOutboundMessage,
    ) -> Mapping[str, Any]:
        return {
            "channel": self.channel.value,
            "conversationId": str(message.conversation_id),
            "messageId": str(message.message_id),
            "correlationId": str(message.correlation_id),
            "text": message.text,
            "status": message.status.value,
            "attachmentIds": [str(attachment.id) for attachment in message.attachments],
        }
