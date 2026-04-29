from collections.abc import Mapping
from typing import Any

from app.domain.channels import ChannelInboundMessage
from app.schemas.enums import ChannelType


class WhatsAppAdapter:
    channel = ChannelType.WHATSAPP

    async def normalize_inbound_message(
        self,
        *,
        payload: Mapping[str, Any],
    ) -> ChannelInboundMessage:
        raise NotImplementedError("WhatsApp adapter is a future integration stub")
