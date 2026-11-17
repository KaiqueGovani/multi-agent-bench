"""Read-only model discovery with request-scoped credentials and bounded work."""
import asyncio
import time

from anthropic import AsyncAnthropic, APITimeoutError
from botocore.config import Config
from botocore.session import get_session
from botocore.tokens import FrozenAuthToken

from app.core.config import Settings
from app.schemas.runtime import LlmModelListResponse, LlmModelOption

DISCOVERY_TIMEOUT_SECONDS = 8
MAX_ANTHROPIC_PAGES = 3
MAX_BEDROCK_PAGES = 2


class ModelDiscoveryError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _option(model_id: object, name: object) -> LlmModelOption:
    if (not isinstance(model_id, str) or not model_id or len(model_id) > 512
        or any(character.isspace() or not character.isprintable() for character in model_id)):
        raise ValueError("Invalid model listing")
    if not isinstance(name, str) or not name.strip() or len(name) > 256 or not name.isprintable():
        raise ValueError("Invalid model listing")
    return LlmModelOption(id=model_id, name=name.strip())


async def _anthropic_models(api_key: str) -> list[LlmModelOption]:
    models = {}
    after_id = None
    async with AsyncAnthropic(api_key=api_key, timeout=5, max_retries=0) as client:
        for _ in range(MAX_ANTHROPIC_PAGES):
            page = await client.models.list(limit=1000, **({"after_id": after_id} if after_id else {}))
            if not isinstance(page.data, list):
                raise ValueError("Invalid model listing")
            for model in page.data:
                if getattr(model, "lifecycle", None) == "retired":
                    continue
                option = _option(model.id, model.display_name)
                models.setdefault(option.id, option)
            if not page.has_more:
                break
            cursor = page.last_id
            if not isinstance(cursor, str) or not cursor or cursor == after_id:
                raise ValueError("Invalid model pagination")
            after_id = cursor
    if not models:
        raise ValueError("No models returned")
    return list(models.values())


class _StaticTokenProvider:
    def __init__(self, token: str):
        self.token = FrozenAuthToken(token)

    def load_token(self, **_kwargs):
        return self.token


class _NoAwsCredentials:
    def load_credentials(self):
        return None


def _bedrock_client(api_key: str, region: str):
    # A dedicated session prevents an unsaved key from changing process-wide AWS
    # credentials, and avoids falling back to IAM credentials or instance metadata.
    session = get_session()
    session.register_component("token_provider", _StaticTokenProvider(api_key))
    session.register_component("credential_provider", _NoAwsCredentials())
    return session.create_client("bedrock", region_name=region, config=Config(
        signature_version="bearer", connect_timeout=2, read_timeout=2,
        retries={"total_max_attempts": 1},
    ))


def _bedrock_models(api_key: str, region: str) -> list[LlmModelOption]:
    models = {}
    next_token = None
    deadline = time.monotonic() + DISCOVERY_TIMEOUT_SECONDS
    client = _bedrock_client(api_key, region)
    try:
        for _ in range(MAX_BEDROCK_PAGES):
            if time.monotonic() >= deadline:
                break
            page = client.list_inference_profiles(typeEquals="SYSTEM_DEFINED", maxResults=1000,
                       **({"nextToken": next_token} if next_token else {}))
            if not isinstance(page.get("inferenceProfileSummaries"), list):
                raise ValueError("Invalid model listing")
            for model in page["inferenceProfileSummaries"]:
                model_id = model.get("inferenceProfileId")
                if model.get("status") != "ACTIVE" or not isinstance(model_id, str) or ".anthropic." not in model_id:
                    continue
                option = _option(model_id, model.get("inferenceProfileName", model_id))
                models.setdefault(option.id, option)
            cursor = page.get("nextToken")
            if not cursor:
                break
            if not isinstance(cursor, str) or cursor == next_token or len(cursor) > 2048:
                raise ValueError("Invalid model pagination")
            next_token = cursor
    finally:
        client.close()
    if not models:
        raise ValueError("No models returned")
    return list(models.values())


def bedrock_catalog(settings: Settings) -> list[LlmModelOption]:
    # These geo profile IDs are documented for the listed source regions. The
    # configured model is retained even if custom; catalog entries do not verify
    # this account's permissions or model entitlement.
    models = {settings.bedrock_model_id: _option(settings.bedrock_model_id, "Current Bedrock model")}
    if settings.aws_region in {"us-east-1", "us-east-2", "us-west-1", "us-west-2", "ca-central-1"}:
        models.update({option.id: option for option in (
            _option("us.anthropic.claude-haiku-4-5-20251001-v1:0", "Claude Haiku 4.5 (US)"),
            _option("us.anthropic.claude-sonnet-4-5-20250929-v1:0", "Claude Sonnet 4.5 (US)"),
        )})
    return list(models.values())


async def discover_models(provider: str, api_key: str | None, settings: Settings) -> LlmModelListResponse:
    if provider == "bedrock":
        if api_key:
            try:
                models = await asyncio.wait_for(asyncio.to_thread(_bedrock_models, api_key, settings.aws_region),
                                                timeout=DISCOVERY_TIMEOUT_SECONDS)
                return LlmModelListResponse(provider="bedrock", models=models, source="provider")
            except Exception:
                # Key-specific permissions may allow inference but deny discovery.
                # Degrading to the explicit catalog never claims access was verified.
                pass
        return LlmModelListResponse(provider="bedrock", models=bedrock_catalog(settings), source="catalog")
    if not api_key:
        raise ModelDiscoveryError(400, "Add an Anthropic API key to load available models.")
    try:
        models = await asyncio.wait_for(_anthropic_models(api_key), timeout=DISCOVERY_TIMEOUT_SECONDS)
    except (TimeoutError, APITimeoutError):
        raise ModelDiscoveryError(504, "Model discovery timed out. Try again.") from None
    except Exception:
        raise ModelDiscoveryError(502, "Could not load models from Anthropic. Check the API key and try again.") from None
    return LlmModelListResponse(provider="anthropic", models=models, source="provider")
