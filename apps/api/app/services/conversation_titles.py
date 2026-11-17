"""Once-per-conversation labels, independent of timed agent execution."""
import json
from urllib.request import Request, urlopen
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import ConversationModel, MessageModel, RunModel
from app.db.session import SessionLocal
from app.schemas.enums import ProcessingEventType, ProcessingStatus
from app.services.event_bus import event_bus
from app.services.events import EventService


def fallback_title(text: str | None) -> str:
    return " ".join((text or "Atendimento com anexo").split()[:8])[:80].strip() or "Novo atendimento"


class ConversationTitleService:
    def __init__(self, *, session_factory=None) -> None:
        self._sessions = session_factory or SessionLocal
        self._settings = get_settings()

    def generate_for_first_run(self, *, conversation_id: UUID, message_id: UUID) -> None:
        # Postgres row locking makes this claim durable across requests/workers,
        # including the three parallel architectures belonging to one user turn.
        with self._sessions() as db:
            conversation = db.scalar(select(ConversationModel).where(
                ConversationModel.id == conversation_id).with_for_update())
            if conversation is None:
                return
            metadata = dict(conversation.metadata_json or {})
            if metadata.get("title") or metadata.get("titleGenerationMessageId"):
                return
            requested_message = db.get(MessageModel, message_id)
            if requested_message is None or requested_message.conversation_id != conversation_id:
                return
            mode = (requested_message.metadata_json or {}).get("runtimeMode", self._settings.runtime_mode)
            first_run = db.scalar(select(RunModel).where(RunModel.conversation_id == conversation_id)
                                  .order_by(RunModel.created_at, RunModel.id).limit(1))
            if first_run is None:
                return
            # Existing untitled conversations are named lazily on their next
            # dispatch, still using the original first-run message as the seed.
            message_id = first_run.message_id
            message = db.get(MessageModel, message_id)
            if message is None:
                return
            text = message.content_text
            correlation_id = message.correlation_id
            conversation.metadata_json = {**metadata, "titleGenerationMessageId": str(message_id)}
            db.commit()

        title, source = fallback_title(text), "fallback"
        if mode == "real" and self._settings.ai_runtime_url:
            try:
                headers = {"Content-Type": "application/json"}
                if self._settings.ai_service_secret:
                    headers["X-AI-Service-Secret"] = self._settings.ai_service_secret
                request = Request(self._settings.ai_runtime_url.rstrip("/") + "/conversations/title",
                                  data=json.dumps({"text": (text or "Atendimento com anexo")[:2000]}).encode(),
                                  headers=headers, method="POST")
                with urlopen(request, timeout=10) as response:
                    result = json.load(response)
                candidate = result.get("title") if isinstance(result, dict) else None
                if isinstance(candidate, str) and candidate.strip() and len(candidate) <= 80:
                    title = " ".join(candidate.split())
                    source = "model" if result.get("source") == "model" else "fallback"
            except Exception:
                # Naming must never block or fail a customer's actual run.
                pass

        with self._sessions() as db:
            conversation = db.scalar(select(ConversationModel).where(
                ConversationModel.id == conversation_id).with_for_update())
            if conversation is None:  # It may have been deleted while naming.
                return
            metadata = dict(conversation.metadata_json or {})
            if metadata.get("title"):
                return
            conversation.metadata_json = {**metadata, "title": title, "titleSource": source}
            event = EventService(db).record_event(
                conversation_id=conversation_id, message_id=message_id,
                correlation_id=correlation_id, event_type=ProcessingEventType.CONVERSATION_UPDATED,
                status=ProcessingStatus.COMPLETED, payload={"title": title, "titleSource": source},
                commit=False, publish=False,
            )
            db.commit()
        event_bus.publish(event)
