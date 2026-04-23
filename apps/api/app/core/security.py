import secrets

from fastapi import Header, HTTPException, Query, Request, status

from app.core.config import get_settings


async def verify_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    query_api_key: str | None = Query(default=None, alias="apiKey"),
) -> None:
    settings = get_settings()
    if not settings.api_key:
        return

    provided_key = x_api_key or query_api_key
    if provided_key and secrets.compare_digest(provided_key, settings.api_key):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )


async def verify_ai_service_secret(
    x_ai_service_secret: str | None = Header(default=None, alias="X-AI-Service-Secret"),
) -> None:
    settings = get_settings()
    if not settings.ai_service_secret:
        return

    if x_ai_service_secret and secrets.compare_digest(
        x_ai_service_secret,
        settings.ai_service_secret,
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing AI service secret",
        headers={"WWW-Authenticate": "ApiKey"},
    )
