from collections.abc import Mapping
from typing import Any

from app.schemas.domain import NormalizedOutboundMessage
from app.schemas.enums import ChannelType


class WhatsAppOutboundAdapter:
    channel = ChannelType.WHATSAPP

    def format_outbound_message(
        self,
        message: NormalizedOutboundMessage,
    ) -> Mapping[str, Any]:
        raise NotImplementedError("WhatsApp outbound adapter is a future integration stub")
