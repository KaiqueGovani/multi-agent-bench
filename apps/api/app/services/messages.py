import hashlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.storage import StorageAdapter, get_storage_adapter
from app.core.config import get_settings
from app.db.mappers import attachment_to_schema, message_to_schema
from app.db.models import AttachmentModel, ConversationModel, MessageModel
from app.domain.channels import ChannelAttachment, ChannelInboundMessage
from app.schemas.api import SendMessageResponse
from app.schemas.domain import Attachment, Message
from app.schemas.enums import (
    AttachmentStatus,
    MessageDirection,
    MessageStatus,
    ProcessingEventType,
    ProcessingStatus,
)
from app.services.event_bus import event_bus
from app.services.events import EventService
from app.services.file_metadata import detect_image_dimensions, detect_pdf_page_count


SUPPORTED_ATTACHMENT_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}


class MessageValidationError(ValueError):
    pass


class MessageService:
    def __init__(self, db: Session, storage: StorageAdapter | None = None) -> None:
        self._db = db
        self._storage = storage or get_storage_adapter()
        self._settings = get_settings()

    def create_message(
        self,
        *,
        inbound: ChannelInboundMessage,
    ) -> SendMessageResponse:
        self._validate_message(text=inbound.text, attachments=inbound.attachments)
        if inbound.conversation_id is None:
            raise MessageValidationError("Conversation is required")

        conversation = self._db.get(ConversationModel, inbound.conversation_id)
        if conversation is None:
            raise MessageValidationError("Conversation not found")

        correlation_id = uuid4()
        now = datetime.now(UTC)
        metadata = inbound.metadata.model_copy(
            update={
                "architecture_mode": (
                    inbound.metadata.architecture_mode
                    or self._settings.default_architecture_mode
                ),
                "channel": inbound.channel,
                "correlation_id": correlation_id,
                "runtime_mode": inbound.metadata.runtime_mode or self._settings.runtime_mode,
            }
        )
        metadata_json = metadata.model_dump(
            by_alias=True,
            mode="json",
            exclude_none=True,
        )

        message = MessageModel(
            id=uuid4(),
            conversation_id=inbound.conversation_id,
            direction=MessageDirection.INBOUND.value,
            content_text=inbound.text,
            created_at_client=inbound.created_at_client,
            created_at_server=now,
            status=MessageStatus.ACCEPTED.value,
            correlation_id=correlation_id,
            metadata_json=metadata_json,
        )
        self._db.add(message)
        conversation.updated_at = now
        self._db.flush()

        event_service = EventService(self._db)
        events = [
            event_service.record_event(
                conversation_id=inbound.conversation_id,
                message_id=message.id,
                event_type=ProcessingEventType.MESSAGE_RECEIVED,
                correlation_id=correlation_id,
                status=ProcessingStatus.COMPLETED,
                payload={
                    "architectureMode": metadata.architecture_mode,
                    "channel": inbound.channel.value,
                    "correlationId": str(correlation_id),
                    "textLength": len(inbound.text or ""),
                    "fileCount": len(inbound.attachments),
                    "requestId": str(metadata.request_id) if metadata.request_id else None,
                    "runtimeMode": metadata.runtime_mode,
                },
                commit=False,
                publish=False,
            )
        ]

        for incoming in inbound.attachments:
            events.extend(
                self._persist_attachment(
                    event_service=event_service,
                    conversation_id=inbound.conversation_id,
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
        incoming: ChannelAttachment,
    ):
        upload_started = event_service.record_event(
            conversation_id=conversation_id,
            message_id=message_id,
            event_type=ProcessingEventType.ATTACHMENT_UPLOAD_STARTED,
            correlation_id=correlation_id,
            status=ProcessingStatus.RUNNING,
            payload={
                "filename": incoming.original_filename,
                "mimeType": incoming.mime_type,
            },
            commit=False,
            publish=False,
        )

        self._validate_attachment(incoming)
        checksum = f"sha256:{hashlib.sha256(incoming.content).hexdigest()}"
        width, height = detect_image_dimensions(incoming.mime_type, incoming.content)
        page_count = (
            detect_pdf_page_count(incoming.content)
            if incoming.mime_type == "application/pdf"
            else None
        )
        attachment_id = uuid4()
        stored_file = self._storage.save(
            conversation_id=conversation_id,
            message_id=message_id,
            attachment_id=attachment_id,
            original_filename=incoming.original_filename,
            content=incoming.content,
        )

        metadata_json = incoming.metadata.model_dump(
            by_alias=True,
            mode="json",
            exclude_none=True,
        )
        metadata_json.update(
            {
                "storageProvider": stored_file.provider,
                "storageBucket": stored_file.bucket,
                "objectKey": stored_file.storage_key,
                "pageCount": page_count,
            }
        )

        attachment = AttachmentModel(
            id=attachment_id,
            message_id=message_id,
            storage_key=stored_file.storage_key,
            original_filename=incoming.original_filename,
            mime_type=incoming.mime_type,
            size_bytes=len(incoming.content),
            checksum=checksum,
            width=width,
            height=height,
            status=AttachmentStatus.VALIDATED.value,
            metadata_json=metadata_json,
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
                "filename": incoming.original_filename,
                "mimeType": incoming.mime_type,
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
                "width": attachment.width,
                "height": attachment.height,
                "pageCount": page_count,
            },
            commit=False,
            publish=False,
        )

        return [
            upload_started,
            upload_completed,
            validation_started,
            validation_completed,
        ]

    def _validate_message(self, *, text: str | None, attachments: list[ChannelAttachment]) -> None:
        if not (text and text.strip()) and not attachments:
            raise MessageValidationError("Message must include text or at least one file")
        if len(attachments) > self._settings.max_files_per_message:
            raise MessageValidationError(
                f"At most {self._settings.max_files_per_message} files are allowed per message"
            )

    def _validate_attachment(self, attachment: ChannelAttachment) -> None:
        if attachment.mime_type not in SUPPORTED_ATTACHMENT_MIME_TYPES:
            raise MessageValidationError(
                f"Unsupported file type: {attachment.mime_type}"
            )
        if len(attachment.content) > self._settings.max_file_size_bytes:
            raise MessageValidationError(
                f"File exceeds maximum size of {self._settings.max_file_size_bytes} bytes"
            )
        if not attachment.content:
            raise MessageValidationError("Empty files are not allowed")
