import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.storage import LocalStorageAdapter
from app.core.config import get_settings
from app.db.mappers import attachment_to_schema, message_to_schema
from app.db.models import AttachmentModel, ConversationModel, MessageModel
from app.schemas.api import SendMessageResponse
from app.schemas.domain import Attachment, Message, OperationalMetadata
from app.schemas.enums import (
    AttachmentStatus,
    MessageDirection,
    MessageStatus,
    ProcessingEventType,
    ProcessingStatus,
)
from app.services.event_bus import event_bus
from app.services.events import EventService


SUPPORTED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


@dataclass(frozen=True)
class IncomingAttachment:
    filename: str
    content_type: str
    content: bytes


class MessageValidationError(ValueError):
    pass


class MessageService:
    def __init__(self, db: Session, storage: LocalStorageAdapter | None = None) -> None:
        self._db = db
        self._storage = storage or LocalStorageAdapter()
        self._settings = get_settings()

    def create_message(
        self,
        *,
        conversation_id: UUID,
        text: str | None,
        metadata: OperationalMetadata,
        attachments: list[IncomingAttachment],
    ) -> SendMessageResponse:
        self._validate_message(text=text, attachments=attachments)

        conversation = self._db.get(ConversationModel, conversation_id)
        if conversation is None:
            raise MessageValidationError("Conversation not found")

        correlation_id = uuid4()
        now = datetime.now(UTC)
        metadata_json = metadata.model_dump(
            by_alias=True,
            mode="json",
            exclude_none=True,
        )

        message = MessageModel(
            id=uuid4(),
            conversation_id=conversation_id,
            direction=MessageDirection.INBOUND.value,
            content_text=text,
            created_at_client=metadata.client_timestamp,
            created_at_server=now,
            status=MessageStatus.ACCEPTED.value,
            correlation_id=correlation_id,
            metadata_json=metadata_json,
        )
        self._db.add(message)
        self._db.flush()

        event_service = EventService(self._db)
        events = [
            event_service.record_event(
                conversation_id=conversation_id,
                message_id=message.id,
                event_type=ProcessingEventType.MESSAGE_RECEIVED,
                correlation_id=correlation_id,
                status=ProcessingStatus.COMPLETED,
                payload={
                    "textLength": len(text or ""),
                    "fileCount": len(attachments),
                },
                commit=False,
                publish=False,
            )
        ]

        for incoming in attachments:
            events.extend(
                self._persist_attachment(
                    event_service=event_service,
                    conversation_id=conversation_id,
                    message_id=message.id,
                    correlation_id=correlation_id,
                    incoming=incoming,
                )
            )

        self._db.commit()
        self._db.refresh(message)
        for event in events:
            event_bus.publish(event)

        return SendMessageResponse(
            message_id=message.id,
            conversation_id=message.conversation_id,
            status=MessageStatus(message.status),
            correlation_id=message.correlation_id,
            accepted_at=message.created_at_server,
        )

    def list_conversation_messages(self, conversation_id: UUID) -> list[Message]:
        statement = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at_server, MessageModel.id)
        )
        return [message_to_schema(message) for message in self._db.scalars(statement).all()]

    def list_conversation_attachments(self, conversation_id: UUID) -> list[Attachment]:
        statement = (
            select(AttachmentModel)
            .join(MessageModel, MessageModel.id == AttachmentModel.message_id)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(AttachmentModel.created_at, AttachmentModel.id)
        )
        return [
            attachment_to_schema(attachment)
            for attachment in self._db.scalars(statement).all()
        ]

    def _persist_attachment(
        self,
        *,
        event_service: EventService,
        conversation_id: UUID,
        message_id: UUID,
        correlation_id: UUID,
        incoming: IncomingAttachment,
    ):
        upload_started = event_service.record_event(
            conversation_id=conversation_id,
            message_id=message_id,
            event_type=ProcessingEventType.ATTACHMENT_UPLOAD_STARTED,
            correlation_id=correlation_id,
            status=ProcessingStatus.RUNNING,
            payload={
                "filename": incoming.filename,
                "mimeType": incoming.content_type,
            },
            commit=False,
            publish=False,
        )

        self._validate_attachment(incoming)
        checksum = f"sha256:{hashlib.sha256(incoming.content).hexdigest()}"
        attachment_id = uuid4()
        stored_file = self._storage.save(
            conversation_id=conversation_id,
            message_id=message_id,
            attachment_id=attachment_id,
            original_filename=incoming.filename,
            content=incoming.content,
        )

        attachment = AttachmentModel(
            id=attachment_id,
            message_id=message_id,
            storage_key=stored_file.storage_key,
            original_filename=incoming.filename,
            mime_type=incoming.content_type,
            size_bytes=len(incoming.content),
            checksum=checksum,
            status=AttachmentStatus.VALIDATED.value,
            metadata_json={},
        )
        self._db.add(attachment)
        self._db.flush()

        upload_completed = event_service.record_event(
            conversation_id=conversation_id,
            message_id=message_id,
            event_type=ProcessingEventType.ATTACHMENT_UPLOAD_COMPLETED,
            correlation_id=correlation_id,
            status=ProcessingStatus.COMPLETED,
            payload={
                "attachmentId": str(attachment.id),
                "storageKey": attachment.storage_key,
            },
            commit=False,
            publish=False,
        )

        validation_started = event_service.record_event(
            conversation_id=conversation_id,
            message_id=message_id,
            event_type=ProcessingEventType.ATTACHMENT_VALIDATION_STARTED,
            correlation_id=correlation_id,
            status=ProcessingStatus.RUNNING,
            payload={
                "attachmentId": str(attachment.id),
                "filename": incoming.filename,
                "mimeType": incoming.content_type,
                "sizeBytes": len(incoming.content),
            },
            commit=False,
            publish=False,
        )

        validation_completed = event_service.record_event(
            conversation_id=conversation_id,
            message_id=message_id,
            event_type=ProcessingEventType.ATTACHMENT_VALIDATION_COMPLETED,
            correlation_id=correlation_id,
            status=ProcessingStatus.COMPLETED,
            payload={
                "attachmentId": str(attachment.id),
                "mimeType": attachment.mime_type,
                "sizeBytes": attachment.size_bytes,
                "checksum": attachment.checksum,
            },
            commit=False,
            publish=False,
        )

        return [
            upload_started,
            validation_started,
            validation_completed,
            upload_completed,
        ]

    def _validate_message(self, *, text: str | None, attachments: list[IncomingAttachment]) -> None:
        if not (text and text.strip()) and not attachments:
            raise MessageValidationError("Message must include text or at least one file")
        if len(attachments) > self._settings.max_files_per_message:
            raise MessageValidationError(
                f"At most {self._settings.max_files_per_message} files are allowed per message"
            )

    def _validate_attachment(self, attachment: IncomingAttachment) -> None:
        if attachment.content_type not in SUPPORTED_IMAGE_MIME_TYPES:
            raise MessageValidationError(
                f"Unsupported file type: {attachment.content_type}"
            )
        if len(attachment.content) > self._settings.max_file_size_bytes:
            raise MessageValidationError(
                f"File exceeds maximum size of {self._settings.max_file_size_bytes} bytes"
            )
        if not attachment.content:
            raise MessageValidationError("Empty files are not allowed")
