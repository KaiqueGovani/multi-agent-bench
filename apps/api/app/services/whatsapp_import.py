"""Persist a selected conversation prefix atomically, then dispatch only its target."""
import hashlib
import json
import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4, uuid5
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.inbound.whatsapp import WhatsAppAdapter
from app.core.config import get_settings
from app.db.models import ConversationModel, MessageModel, RunModel
from app.schemas.domain import OperationalMetadata
from app.schemas.enums import ConversationStatus, ProcessingEventType, ProcessingStatus
from app.schemas.whatsapp import WhatsAppImportRequest, WhatsAppImportResponse
from app.services.events import EventService
from app.services.run_configuration import WHATSAPP_APPLICATION_PROTOCOL, _build_run_experiment, _expand_architecture_keys

IMPORT_NAMESPACE = UUID("de366871-74d2-4c72-b39d-fa6733ac1d93")


class WhatsAppImportConflict(ValueError):
    pass


class WhatsAppRuntimeUnavailable(ValueError):
    pass


def check_live_runtime(url: str | None) -> None:
    if not url:
        raise WhatsAppRuntimeUnavailable("Real runtime is not configured; mock fallback is disabled for imports")
    try:
        with urlopen(url.rstrip("/") + "/health", timeout=2) as response:
            health = json.load(response)
        if not isinstance(health, dict) or health.get("llm", {}).get("ready") is not True:
            raise WhatsAppRuntimeUnavailable("Real runtime is not ready; enable live LLM and configure its credentials")
    except (HTTPError, URLError, OSError, ValueError, AttributeError) as exc:
        if isinstance(exc, WhatsAppRuntimeUnavailable):
            raise
        raise WhatsAppRuntimeUnavailable("Cannot verify real runtime readiness; no capture was imported") from exc


class WhatsAppImportService:
    def __init__(self, db: Session):
        self.db = db

    async def import_capture(self, request: WhatsAppImportRequest) -> WhatsAppImportResponse:
        conversation_id = uuid5(IMPORT_NAMESPACE, str(request.capture_id))
        prefix = request.prefix()
        canonical = request.model_dump(mode="json", by_alias=True)
        canonical["messages"] = [m.model_dump(mode="json", by_alias=True) for m in prefix]
        digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        existing = self.db.get(ConversationModel, conversation_id)
        if existing:
            return self._existing(existing, digest)
        settings = get_settings()
        if request.runtime_mode == "real":
            await asyncio.to_thread(check_live_runtime, settings.ai_runtime_url)

        now, correlation_id = datetime.now(UTC), uuid4()
        architectures = _expand_architecture_keys(request.architecture_mode)
        ids = [uuid4() for _ in architectures]
        message_ids = [uuid4() for _ in prefix]
        metadata = {
            "source": request.source, "captureId": str(request.capture_id),
            "chatTitle": request.chat_title, "importPayloadSha256": digest,
            "architectureMode": request.architecture_mode.value,
            "runtimeMode": request.runtime_mode.value,
            "importedMessageCount": len(prefix), "targetSourceId": request.target_source_id,
            "targetMessageId": str(message_ids[-1]), "importRunIds": [str(i) for i in ids],
            "comparisonProtocol": WHATSAPP_APPLICATION_PROTOCOL if request.runtime_mode == "real" else None,
        }
        conversation = ConversationModel(
            id=conversation_id, channel="whatsapp", status=ConversationStatus.ACTIVE.value,
            created_at=now, updated_at=now, metadata_json=metadata,
        )
        self.db.add(conversation)
        try:
            self.db.flush()
            adapter = WhatsAppAdapter()
            for i, captured in enumerate(prefix):
                normalized = await adapter.normalize_inbound_message(payload=captured.model_dump(by_alias=True))
                target = i == len(prefix) - 1
                self.db.add(MessageModel(
                    id=message_ids[i], conversation_id=conversation_id,
                    direction="inbound" if captured.role == "customer" else "outbound",
                    content_text=normalized.text, created_at_client=normalized.created_at_client,
                    created_at_server=now + timedelta(microseconds=i),
                    status="accepted" if target else "completed", correlation_id=correlation_id,
                    metadata_json={
                        **normalized.metadata.model_dump(by_alias=True, mode="json", exclude_none=True),
                        "captureId": str(request.capture_id), "captureSequence": i,
                        "architectureMode": request.architecture_mode.value,
                        "runtimeMode": request.runtime_mode.value,
                    },
                ))
            self.db.flush()
            run_metadata = OperationalMetadata.model_validate({
                "architectureMode": request.architecture_mode.value,
                "runtimeMode": request.runtime_mode.value,
                "experimentId": "whatsapp-demo-v1", "scenarioId": f"whatsapp-{request.capture_id}",
            })
            for i, architecture in enumerate(architectures):
                experiment = _build_run_experiment(
                    run_metadata, architecture_key=architecture, comparison_only=i > 0,
                    text=prefix[-1].text, whatsapp_application=True,
                )
                self.db.add(RunModel(
                    id=ids[i], conversation_id=conversation_id, message_id=message_ids[-1],
                    correlation_id=correlation_id, status="pending", created_at=now, updated_at=now,
                    ai_session_id=f"{conversation_id}:{architecture}:whatsapp-demo-v1",
                    experiment_json=experiment.model_dump(by_alias=True, mode="json", exclude_none=True),
                    summary_json={},
                ))
            event_service = EventService(self.db)
            event_service.record_event(
                conversation_id=conversation_id, correlation_id=correlation_id,
                event_type=ProcessingEventType.CONVERSATION_CREATED, status=ProcessingStatus.COMPLETED,
                payload={"source": request.source, "importedMessageCount": len(prefix)},
                commit=False, publish=False,
            )
            event_service.record_event(
                conversation_id=conversation_id, message_id=message_ids[-1], correlation_id=correlation_id,
                event_type=ProcessingEventType.MESSAGE_RECEIVED, status=ProcessingStatus.COMPLETED,
                payload={"source": request.source, "architectureMode": request.architecture_mode.value,
                         "runtimeMode": request.runtime_mode.value, "fileCount": 0},
                commit=False, publish=False,
            )
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            existing = self.db.get(ConversationModel, conversation_id)
            if existing is None:
                raise
            return self._existing(existing, digest)
        except Exception:
            self.db.rollback()
            raise
        return WhatsAppImportResponse(conversation_id=conversation_id, message_id=message_ids[-1],
                                      run_id=ids[0], run_ids=ids, imported_message_count=len(prefix), reused=False)

    def _existing(self, conversation: ConversationModel, digest: str) -> WhatsAppImportResponse:
        metadata = conversation.metadata_json
        if metadata.get("importPayloadSha256") != digest:
            raise WhatsAppImportConflict("captureId already belongs to a different capture; create a new captureId")
        ids = [UUID(i) for i in metadata["importRunIds"]]
        return WhatsAppImportResponse(conversation_id=conversation.id, message_id=UUID(metadata["targetMessageId"]),
                                      run_id=ids[0], run_ids=ids, imported_message_count=metadata["importedMessageCount"], reused=True)
