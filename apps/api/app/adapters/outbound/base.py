from collections.abc import Mapping
from typing import Any, Protocol

from app.schemas.domain import NormalizedOutboundMessage
from app.schemas.enums import ChannelType


class OutboundChannelAdapter(Protocol):
    channel: ChannelType

    def format_outbound_message(
        self,
        message: NormalizedOutboundMessage,
    ) -> Mapping[str, Any]:
        """Convert an internal outbound message into a channel-specific payload."""
        ...
