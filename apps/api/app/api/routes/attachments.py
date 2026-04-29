from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.adapters.storage import get_storage_adapter
from app.db import get_db_session
from app.db.models import AttachmentModel

router = APIRouter()


@router.get("/{attachment_id}")
def get_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db_session),
) -> Response:
    attachment = db.get(AttachmentModel, attachment_id)
    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    try:
        content = get_storage_adapter().read(attachment.storage_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid attachment storage key",
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment file not found",
        ) from exc

    return Response(
        content=content,
        media_type=attachment.mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{attachment.original_filename}"'
        },
    )
