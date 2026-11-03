"""Exercise actual persistence, import entrypoint, and dispatch history without AWS."""
import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.inbound.whatsapp import WhatsAppAdapter
from app.core.config import get_settings
from app.db import get_db_session
from app.db.base import Base
from app.db.models import ConversationModel, MessageModel, ProcessingEventModel, RunModel
from app.main import create_app
from app.services.processing_dispatcher import ProcessingDispatcher
from app.services.whatsapp_import import check_live_runtime, WhatsAppRuntimeUnavailable


@compiles(JSONB, "sqlite")
def sqlite_jsonb(_element, _compiler, **_kw):
    return "JSON"


@pytest.fixture
def local_api(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-import-key")
    monkeypatch.setenv("RUNTIME_MODE", "mock")
    monkeypatch.delenv("AI_RUNTIME_URL", raising=False)
    get_settings.cache_clear()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = create_app()
    def session():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db_session] = session
    dispatched = []
    monkeypatch.setattr(ProcessingDispatcher, "dispatch_many", lambda self, **kwargs: dispatched.append(kwargs["dispatches"]))
    monkeypatch.setattr("app.services.processing_dispatcher.SessionLocal", factory)
    with TestClient(app) as client:
        yield client, factory, dispatched
    engine.dispose()
    get_settings.cache_clear()


def capture(**changes):
    body = {
        "source": "whatsapp_web", "captureId": str(uuid4()), "chatTitle": "Teste MAB",
        "targetSourceId": "3", "architectureMode": "centralized_orchestration", "runtimeMode": "mock",
        "messages": [
            {"sourceId": "1", "role": "customer", "text": "Bom dia", "timestamp": "2026-10-31T10:00:00-03:00"},
            {"sourceId": "2", "role": "attendant", "text": "Como podemos ajudar?"},
            {"sourceId": "3", "role": "customer", "text": "Vocês têm dipirona?"},
            {"sourceId": "4", "role": "attendant", "text": "RESPOSTA FUTURA EXCLUÍDA"},
        ],
    }
    return {**body, **changes}


def submit(client, body, **kwargs):
    return client.post("/integrations/whatsapp/import", json=body,
                       headers={"X-API-Key": "test-import-key"}, **kwargs)


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_atomic_prefix_preserves_roles_order_timestamp_and_one_target_dispatch(local_api):
    client, factory, dispatched = local_api
    body = capture()
    response = submit(client, body)
    assert response.status_code == 202, response.text
    result = response.json()
    assert result["importedMessageCount"] == 3 and result["reused"] is False
    assert len(dispatched) == 1 and len(dispatched[0]) == 1
    assert str(dispatched[0][0]["message_id"]) == result["messageId"]
    with factory() as db:
        rows = db.scalars(select(MessageModel).order_by(MessageModel.created_at_server)).all()
        assert [r.direction for r in rows] == ["inbound", "outbound", "inbound"]
        assert [r.content_text for r in rows] == [m["text"] for m in body["messages"][:3]]
        assert [r.metadata_json["sourceMessageId"] for r in rows] == ["1", "2", "3"]
        assert all(r.metadata_json["importedHistory"] is True for r in rows)
        assert rows[0].created_at_client.hour == 10
        assert count(db, ConversationModel) == count(db, RunModel) == 1
        assert count(db, ProcessingEventModel) == 2
        assert db.get(ConversationModel, UUID(result["conversationId"])).channel == "whatsapp"
        assert "comparisonProtocol" not in db.get(RunModel, UUID(result["runId"])).experiment_json


def test_retry_reuses_durable_rows_but_rejects_mutated_payload(local_api):
    client, factory, dispatched = local_api
    body = capture()
    first = submit(client, body).json()
    second = submit(client, body).json()
    assert second == {**first, "reused": True}
    # Later messages are outside the selected prefix and cannot affect the run.
    body["messages"][3]["text"] = "Outra resposta futura"
    assert submit(client, body).json()["reused"] is True
    body["messages"][0]["text"] = "Conteúdo alterado"
    assert submit(client, body).status_code == 409
    assert len(dispatched) == 1
    with factory() as db:
        assert count(db, ConversationModel) == count(db, RunModel) == 1
        assert count(db, MessageModel) == 3


def test_all_architectures_share_imported_attendant_history_and_cutoff(local_api):
    client, factory, dispatched = local_api
    messages = [{"sourceId": str(i), "role": "customer" if i % 2 == 0 else "attendant", "text": f"Mensagem {i}"}
                for i in range(13)]
    result = submit(client, capture(messages=messages, targetSourceId="12", architectureMode="all_architectures")).json()
    assert len(result["runIds"]) == 3
    assert len(dispatched) == 1 and len(dispatched[0]) == 3
    with factory() as db:
        target = db.get(MessageModel, UUID(result["messageId"]))
        # A generated sibling response must never become initial context.
        db.add(MessageModel(id=uuid4(), conversation_id=target.conversation_id, direction="outbound",
                            content_text="SIBLING RESPONSE", created_at_server=target.created_at_server + timedelta(seconds=1),
                            status="completed", correlation_id=uuid4(), metadata_json={"architectureMode": "centralized_orchestration"}))
        db.commit()
        dispatcher = ProcessingDispatcher()
        histories = [dispatcher._conversation_history(target.conversation_id, architecture_mode=arch, through_message=target)
                     for arch in ("centralized_orchestration", "structured_workflow", "decentralized_swarm")]
        assert all(len(history) == 13 for history in histories)
        assert all([m.content_text for m in history] == [m["text"] for m in messages] for history in histories)


def test_real_mode_requires_ready_runtime_and_pins_protocol(local_api, monkeypatch):
    client, factory, dispatched = local_api
    body = capture(runtimeMode="real")
    assert submit(client, body).status_code == 503
    with factory() as db:
        assert count(db, ConversationModel) == 0
    monkeypatch.setattr("app.services.whatsapp_import.check_live_runtime", lambda url: None)
    result = submit(client, body)
    assert result.status_code == 202
    with factory() as db:
        run = db.get(RunModel, UUID(result.json()["runId"]))
        assert run.experiment_json["comparisonProtocol"] == "architectural-comparison-v4.4"
        assert run.experiment_json["comparisonSourceProfile"] == "application"
        dispatch = ProcessingDispatcher()._build_runtime_dispatch_request(
            run_model=run, message_model=db.get(MessageModel, run.message_id), traceparent=None, baggage=None,
        ).model_dump(mode="json", by_alias=True)
        assert dispatch["experiment"]["comparisonProtocol"] == "architectural-comparison-v4.4"
        assert dispatch["experiment"]["comparisonSourceProfile"] == "application"


def test_followup_snapshot_includes_new_turn_and_imported_history(local_api):
    client, factory, _ = local_api
    result = submit(client, capture()).json()
    with factory() as db:
        original = db.get(MessageModel, UUID(result["messageId"]))
        followup = MessageModel(id=uuid4(), conversation_id=original.conversation_id, direction="inbound",
                                content_text="E qual o horário?", created_at_server=original.created_at_server + timedelta(seconds=2),
                                status="accepted", correlation_id=uuid4(), metadata_json={})
        db.add(followup)
        db.commit()
        history = ProcessingDispatcher()._conversation_history(original.conversation_id,
                    architecture_mode="structured_workflow", through_message=followup)
        assert len(history) == 4
        assert history[1].direction == "outbound"
        assert history[-1].content_text == "E qual o horário?"


@pytest.mark.parametrize("health", [{"llm": {"ready": False}}, {"llm": None}, {}, []])
def test_live_readiness_fails_closed(monkeypatch, health):
    from io import BytesIO
    import json
    monkeypatch.setattr("app.services.whatsapp_import.urlopen", lambda *args, **kwargs: BytesIO(json.dumps(health).encode()))
    with pytest.raises(WhatsAppRuntimeUnavailable):
        check_live_runtime("http://runtime.test")


def test_live_readiness_accepts_only_ready_runtime(monkeypatch):
    from io import BytesIO
    monkeypatch.setattr("app.services.whatsapp_import.urlopen", lambda *args, **kwargs: BytesIO(b'{"llm":{"ready":true}}'))
    check_live_runtime("http://runtime.test")


@pytest.mark.parametrize("mutation", [
    {"targetSourceId": "not-present"}, {"targetSourceId": "2"}, {"architectureMode": "unknown"},
    {"runtimeMode": "unknown"}, {"messages": []}, {"captureId": "invalid"},
    {"messages": [{"sourceId": "3", "role": "customer", "text": " "}]},
    {"messages": [{"sourceId": "3", "role": "customer", "text": "x", "timestamp": "2026-10-31T10:00:00"}]},
    {"messages": [{"sourceId": "3", "role": "customer", "text": "x"}] * 2},
])
def test_invalid_capture_cannot_persist_or_dispatch(local_api, mutation):
    client, factory, dispatched = local_api
    assert submit(client, capture(**mutation)).status_code == 422
    with factory() as db:
        assert count(db, ConversationModel) == 0
    assert not dispatched


def test_capture_bounds(local_api):
    client, _, dispatched = local_api
    assert submit(client, capture(messages=[{"sourceId": str(i), "role": "customer", "text": "x"}
                                           for i in range(201)])).status_code == 422
    assert submit(client, capture(messages=[{"sourceId": str(i), "role": "customer", "text": "x" * 8000}
                                           for i in range(9)])).status_code == 422
    assert not dispatched


def test_import_requires_api_key_and_extension_cors_remains_protected(local_api):
    client, _, dispatched = local_api
    assert client.post("/integrations/whatsapp/import", json=capture()).status_code == 401
    origin = "chrome-extension://" + "a" * 32
    preflight = client.options("/integrations/whatsapp/import", headers={
        "Origin": origin, "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "X-API-Key,Content-Type",
    })
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == origin
    evil = client.options("/integrations/whatsapp/import", headers={
        "Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST",
    })
    assert evil.status_code == 400
    assert not dispatched


def test_failed_transaction_leaves_no_half_import(local_api, monkeypatch):
    client, factory, dispatched = local_api
    def fail(*args, **kwargs):
        raise RuntimeError("test failure before commit")
    monkeypatch.setattr("app.services.whatsapp_import.EventService.record_event", fail)
    with pytest.raises(RuntimeError):
        submit(client, capture())
    with factory() as db:
        assert count(db, ConversationModel) == count(db, MessageModel) == count(db, RunModel) == 0
    assert not dispatched


def test_whatsapp_adapter_produces_channel_independent_message():
    normalized = asyncio.run(WhatsAppAdapter().normalize_inbound_message(payload={
        "sourceId": "message-source", "role": "customer", "text": "Olá",
    }))
    assert normalized.channel == "whatsapp"
    assert normalized.text == "Olá"
    assert normalized.client_message_id == "message-source"
    assert normalized.metadata.model_extra["sourceRole"] == "customer"
