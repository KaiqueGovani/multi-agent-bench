from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.get("/{attachment_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def get_attachment(attachment_id: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Attachment retrieval will be implemented with storage support in execution step 6.",
    )

