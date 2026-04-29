from typing import Protocol

from app.domain.channels import ChannelInboundMessage
from app.schemas.enums import ChannelType


class ChannelAdapter(Protocol):
    channel: ChannelType

    async def normalize_inbound_message(self, **kwargs) -> ChannelInboundMessage:
        """Convert channel-specific input into the internal message model."""
        ...
