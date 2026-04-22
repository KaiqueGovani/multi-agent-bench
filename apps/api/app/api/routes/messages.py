from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.post("", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def send_message() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Message multipart handling will be implemented in execution step 5.",
    )

