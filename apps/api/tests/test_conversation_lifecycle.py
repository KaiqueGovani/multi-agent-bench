"""Conversation deletion and once-only naming use isolated local persistence."""
from io import BytesIO
import json
from pathlib import Path
from uuid import UUID, uuid4
from threading import Event
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tests.test_whatsapp_import import capture, sqlite_jsonb  # Register JSONB's SQLite compiler.
from app.core.config import get_settings
from app.db import get_db_session
from app.db.base import Base
from app.db.models import (AttachmentModel, ConversationModel, MessageModel, ProcessingEventModel,
                           ReviewTaskModel, RunExecutionEventModel, RunExecutionProjectionModel, RunModel)
from app.main import create_app
from app.services.conversation_titles import ConversationTitleService
from app.services.processing_dispatcher import ProcessingDispatcher


AUTH = {"X-API-Key": "lifecycle-test-key", "X-AI-Service-Secret": "lifecycle-secret"}


@pytest.fixture
def lifecycle(monkeypatch, tmp_path):
    monkeypatch.setenv("API_KEY", AUTH["X-API-Key"])
    monkeypatch.setenv("AI_SERVICE_SECRET", AUTH["X-AI-Service-Secret"])
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path / "storage"))
    monkeypatch.setenv("STORAGE_PROVIDER", "local")
    monkeypatch.setenv("RUNTIME_MODE", "mock")
    monkeypatch.setenv("AI_RUNTIME_URL", "http://runtime.test")
    get_settings.cache_clear()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = create_app()
    def session():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db_session] = session
    monkeypatch.setattr(ProcessingDispatcher, "dispatch_many", lambda *_args, **_kwargs: None)
    with TestClient(app) as client:
        yield client, factory, tmp_path
    engine.dispose()
    get_settings.cache_clear()


def create(client, *, text="Vocês têm dipirona em estoque?", files=False, runtime="mock"):
    response = client.post("/conversations", headers=AUTH, json={"metadata": {"architectureMode": "all_architectures"}})
    cid = response.json()["conversationId"]
    result = client.post("/messages", headers=AUTH,
                        data={"conversationId": cid, "text": text, "metadata_json": json.dumps({
                            "architectureMode": "all_architectures", "runtimeMode": runtime})},
                        files={"files": ("receita.pdf", b"%PDF-1.4\n/Type /Page\n", "application/pdf")} if files else None)
    assert result.status_code == 202, result.text
    return UUID(cid), UUID(result.json()["messageId"]), UUID(result.json()["runId"])


def test_delete_cascades_every_related_record_and_file_preserves_other_conversation(lifecycle):
    client, factory, _ = lifecycle
    cid, mid, rid = create(client, files=True)
    other, _, _ = create(client, text="Qual o horário de atendimento?")
    with factory() as db:
        attachment = db.scalar(select(AttachmentModel).join(MessageModel).where(MessageModel.conversation_id == cid))
        path = Path(get_settings().local_storage_path) / attachment.storage_key
        assert path.is_file()
        db.add(ReviewTaskModel(id=uuid4(), conversation_id=cid, message_id=mid, reason="test", status="open", metadata_json={}))
        db.add(RunExecutionProjectionModel(run_id=rid, conversation_id=cid, message_id=mid,
               architecture_mode="centralized_orchestration", run_status="running", architecture_view_json={},
               metrics_json={}, state_json={}))
        db.add(RunExecutionEventModel(id=uuid4(), run_id=rid, conversation_id=cid, message_id=mid,
               correlation_id=uuid4(), event_family="agent", event_name="started", sequence_no=1,
               status="running", payload_json={}))
        db.commit()
    assert client.delete(f"/conversations/{cid}").status_code == 401
    response = client.delete(f"/conversations/{cid}", headers=AUTH)
    assert response.status_code == 204 and response.content == b""
    assert not path.exists()
    assert client.get(f"/conversations/{cid}", headers=AUTH).status_code == 404
    assert client.get(f"/runs/{rid}", headers=AUTH).status_code == 404
    assert client.delete(f"/conversations/{cid}", headers=AUTH).status_code == 404
    assert client.get(f"/conversations/{other}", headers=AUTH).status_code == 200
    with factory() as db:
        for model in (RunModel, MessageModel, ProcessingEventModel, ReviewTaskModel,
                      RunExecutionEventModel, RunExecutionProjectionModel):
            assert db.scalar(select(func.count()).select_from(model).where(model.conversation_id == cid)) == 0
        assert db.scalar(select(func.count()).select_from(AttachmentModel)) == 0


def test_late_callbacks_and_messages_cannot_resurrect_deleted_conversation(lifecycle):
    client, factory, _ = lifecycle
    cid, mid, rid = create(client)
    assert client.delete(f"/conversations/{cid}", headers=AUTH).status_code == 204
    callback = {"runId": str(rid), "conversationId": str(cid), "messageId": str(mid),
                "correlationId": str(uuid4()), "eventFamily": "response", "eventName": "final",
                "status": "completed", "payload": {"contentText": "Late response"}}
    assert client.post("/integrations/ai/run-events", headers=AUTH, json=callback).status_code == 404
    assert client.patch(f"/runs/{rid}", headers=AUTH, json={"status": "completed"}).status_code == 404
    assert client.post("/messages", headers=AUTH, data={"conversationId": str(cid), "text": "Hello"}).status_code == 404
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(ConversationModel)) == 0
        assert db.scalar(select(func.count()).select_from(MessageModel)) == 0


def test_delete_imported_whatsapp_conversation_removes_prefix_and_run(lifecycle):
    client, factory, _ = lifecycle
    result = client.post("/integrations/whatsapp/import", headers=AUTH, json=capture())
    assert result.status_code == 202, result.text
    cid, rid = result.json()["conversationId"], result.json()["runId"]
    assert client.delete(f"/conversations/{cid}", headers=AUTH).status_code == 204
    assert client.get(f"/runs/{rid}", headers=AUTH).status_code == 404
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(ConversationModel)) == 0
        assert db.scalar(select(func.count()).select_from(MessageModel)) == 0


def test_s3_storage_delete_uses_recorded_bucket():
    from app.adapters.storage.s3 import S3CompatibleStorageAdapter
    calls = []
    adapter = S3CompatibleStorageAdapter.__new__(S3CompatibleStorageAdapter)
    adapter._bucket = "original-attachment-bucket"
    adapter._client = type("Client", (), {"delete_object": lambda _self, **kwargs: calls.append(kwargs)})()
    adapter.delete("attachments/test/object.pdf")
    assert calls == [{"Bucket": "original-attachment-bucket", "Key": "attachments/test/object.pdf"}]


def test_title_work_does_not_delay_parallel_dispatch_or_fail_chat(monkeypatch):
    dispatched = Event()
    calls = []
    def title(**_kwargs):
        assert dispatched.wait(timeout=2), "Run dispatch was blocked by title generation"
        raise RuntimeError("Naming failure is independent of chat")
    monkeypatch.setattr("app.services.processing_dispatcher.ConversationTitleService",
                        lambda **_kwargs: SimpleNamespace(generate_for_first_run=title))
    dispatcher = ProcessingDispatcher()
    def dispatch(**kwargs):
        calls.append(kwargs)
        dispatched.set()
    monkeypatch.setattr(dispatcher, "dispatch", dispatch)
    items = [{"conversation_id": uuid4(), "message_id": uuid4(), "correlation_id": uuid4(), "run_id": uuid4()}
             for _ in range(3)]
    dispatcher.dispatch_many(dispatches=items)
    assert len(calls) == 3


def test_invalid_file_reference_does_not_delete_another_conversation_file(lifecycle):
    client, factory, tmp = lifecycle
    cid, _, _ = create(client, files=True)
    outside = tmp / "keep.pdf"
    outside.write_bytes(b"keep")
    with factory() as db:
        attachment = db.scalar(select(AttachmentModel))
        attachment.storage_key = str(outside)
        db.commit()
    assert client.delete(f"/conversations/{cid}", headers=AUTH).status_code == 503
    assert outside.read_bytes() == b"keep"
    assert client.get(f"/conversations/{cid}", headers=AUTH).status_code == 200


def test_storage_failure_keeps_database_references_for_retry(lifecycle, monkeypatch):
    client, _, _ = lifecycle
    cid, _, _ = create(client, files=True)
    def fail(*_args):
        raise OSError("storage unavailable")
    monkeypatch.setattr("app.adapters.storage.local.LocalStorageAdapter.delete", fail)
    assert client.delete(f"/conversations/{cid}", headers=AUTH).status_code == 503
    assert client.get(f"/conversations/{cid}", headers=AUTH).status_code == 200


def test_first_run_title_generated_once_and_visible_in_detail_and_list(lifecycle, monkeypatch):
    client, factory, _ = lifecycle
    cid, mid, _ = create(client, runtime="real")
    calls = []
    def generate(request, timeout):
        calls.append(json.loads(request.data))
        assert request.full_url == "http://runtime.test/conversations/title"
        assert request.get_header("X-ai-service-secret") == "lifecycle-secret"
        return BytesIO(b'{"title":"Disponibilidade de dipirona","source":"model"}')
    monkeypatch.setattr("app.services.conversation_titles.urlopen", generate)
    service = ConversationTitleService(session_factory=factory)
    # Three architecture dispatches claim the same conversation only once.
    for _ in range(3):
        service.generate_for_first_run(conversation_id=cid, message_id=mid)
    assert len(calls) == 1
    assert client.get(f"/conversations/{cid}", headers=AUTH).json()["conversation"]["title"] == "Disponibilidade de dipirona"
    assert client.get("/conversations", headers=AUTH).json()["conversations"][0]["title"] == "Disponibilidade de dipirona"
    with factory() as db:
        metadata = db.get(ConversationModel, cid).metadata_json
        assert metadata["titleSource"] == "model"
        events = db.scalars(select(ProcessingEventModel).where(ProcessingEventModel.event_type == "conversation.updated")).all()
        assert len(events) == 1 and events[0].payload_json["title"] == metadata["title"]


def test_title_failure_uses_fallback_and_does_not_fail_run(lifecycle, monkeypatch):
    client, factory, _ = lifecycle
    cid, mid, rid = create(client, runtime="real")
    def fail(*_args, **_kwargs):
        raise OSError("provider unavailable")
    monkeypatch.setattr("app.services.conversation_titles.urlopen", fail)
    ConversationTitleService(session_factory=factory).generate_for_first_run(conversation_id=cid, message_id=mid)
    with factory() as db:
        assert db.get(ConversationModel, cid).metadata_json["title"] == "Vocês têm dipirona em estoque?"
        assert db.get(RunModel, rid).status == "pending"


def test_existing_untitled_conversation_is_named_from_first_message_on_next_dispatch(lifecycle, monkeypatch):
    client, factory, _ = lifecycle
    cid, first_mid, _ = create(client, runtime="mock")
    later = client.post("/messages", headers=AUTH, data={"conversationId": str(cid),
           "text": "E qual o horário de vocês?", "metadata_json": '{"runtimeMode":"real"}'})
    assert later.status_code == 202
    requests = []
    def generate(request, timeout):
        requests.append(json.loads(request.data))
        return BytesIO(b'{"title":"Consulta de dipirona","source":"model"}')
    monkeypatch.setattr("app.services.conversation_titles.urlopen", generate)
    ConversationTitleService(session_factory=factory).generate_for_first_run(
        conversation_id=cid, message_id=UUID(later.json()["messageId"]))
    assert requests == [{"text": "Vocês têm dipirona em estoque?"}]
    with factory() as db:
        metadata = db.get(ConversationModel, cid).metadata_json
        assert metadata["titleGenerationMessageId"] == str(first_mid)
        assert metadata["title"] == "Consulta de dipirona"


def test_title_result_after_deletion_does_not_recreate_rows(lifecycle, monkeypatch):
    client, factory, _ = lifecycle
    cid, mid, _ = create(client, runtime="real")
    def generate(*_args, **_kwargs):
        assert client.delete(f"/conversations/{cid}", headers=AUTH).status_code == 204
        return BytesIO(b'{"title":"Never recreated","source":"model"}')
    monkeypatch.setattr("app.services.conversation_titles.urlopen", generate)
    ConversationTitleService(session_factory=factory).generate_for_first_run(conversation_id=cid, message_id=mid)
    assert client.get(f"/conversations/{cid}", headers=AUTH).status_code == 404


def test_local_storage_rejects_sibling_directory_symlink(tmp_path):
    from app.adapters.storage.local import LocalStorageAdapter
    root = tmp_path / "storage"
    root.mkdir()
    sibling = tmp_path / "storage-other"
    sibling.mkdir()
    target = sibling / "private.txt"
    target.write_text("preserve")
    (root / "link").symlink_to(sibling, target_is_directory=True)
    with pytest.raises(ValueError):
        LocalStorageAdapter(str(root)).delete("link/private.txt")
    assert target.read_text() == "preserve"


def test_local_storage_rejects_internal_symlink_to_other_attachment(tmp_path):
    from app.adapters.storage.local import LocalStorageAdapter
    target = tmp_path / "other" / "private.txt"
    target.parent.mkdir()
    target.write_text("preserve")
    (tmp_path / "link").symlink_to(target.parent, target_is_directory=True)
    with pytest.raises(ValueError):
        LocalStorageAdapter(str(tmp_path)).delete("link/private.txt")
    assert target.read_text() == "preserve"
