"""Persisted handoffs work without the runtime emitting a dedicated review event."""
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.db.models import ConversationModel, MessageModel, ReviewTaskModel, RunModel
from app.services.reviews import ReviewService
from tests.test_conversation_lifecycle import AUTH, create, lifecycle


REVIEW_COMPLETION = {"status": "human_review_required", "humanReviewRequired": True,
                     "finalOutcome": "human_review_required"}


def complete(client, rid):
    response = client.patch(f"/runs/{rid}", headers=AUTH, json=REVIEW_COMPLETION)
    assert response.status_code == 200, response.text
    return response.json()


def execution_event(client, cid, mid, rid, family, name, *, payload=None):
    response = client.post("/integrations/ai/run-events", headers=AUTH, json={
        "runId": str(rid), "conversationId": str(cid), "messageId": str(mid),
        "correlationId": str(mid), "eventFamily": family, "eventName": name,
        "status": "running" if name == "started" else "failed" if name == "failed" else "completed",
        "source": "ai_service", "payload": payload or {},
    })
    assert response.status_code == 202, response.text
    return response.json()


@pytest.mark.parametrize("channel", ["web_chat", "whatsapp"])
def test_completion_alone_creates_visible_handoff_without_projection(lifecycle, channel):
    client, factory, _ = lifecycle
    cid, mid, rid = create(client)
    with factory() as db:
        db.get(ConversationModel, cid).channel = channel
        db.commit()
    complete(client, rid)
    complete(client, rid)
    detail = client.get(f"/conversations/{cid}", headers=AUTH).json()
    assert detail["conversation"]["status"] == "human_review_required"
    assert next(message for message in detail["messages"] if message["id"] == str(mid))["status"] == "human_review_required"
    assert len(detail["reviewTasks"]) == 1
    assert detail["reviewTasks"][0]["metadata"]["runtimeRunId"] == str(rid)
    assert detail["reviewTasks"][0]["metadata"]["sourceMessageId"] == str(mid)
    queue = client.get("/reviews", headers=AUTH).json()["reviewTasks"]
    assert [task["id"] for task in queue] == [detail["reviewTasks"][0]["id"]]
    summary = client.get("/conversations", headers=AUTH).json()["conversations"][0]
    assert summary["reviewPending"] is True


def test_final_response_review_event_and_completion_share_one_task(lifecycle):
    client, factory, _ = lifecycle
    cid, mid, rid = create(client)
    final = execution_event(client, cid, mid, rid, "response", "final",
                            payload={"contentText": "Uma proposta para avaliação humana.", "reviewRequired": True})
    assert final["payload"]["reviewTaskId"]
    execution_event(client, cid, mid, rid, "review", "required", payload={"reason": "Needs assessment"})
    complete(client, rid)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(ReviewTaskModel)) == 1
        assert db.get(ConversationModel, cid).status == "human_review_required"


def test_comparison_runs_do_not_create_global_handoffs_or_change_canonical_state(lifecycle):
    client, factory, _ = lifecycle
    cid, mid, rid = create(client)
    with factory() as db:
        comparison = next(run for run in db.scalars(select(RunModel).where(RunModel.message_id == mid))
                          if run.experiment_json.get("comparisonOnly"))
        other_id = comparison.id
        original_state = db.get(ConversationModel, cid).status
    complete(client, other_id)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(ReviewTaskModel)) == 0
        assert db.get(ConversationModel, cid).status == original_state
    complete(client, rid)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(ReviewTaskModel)) == 1


@pytest.mark.parametrize("resolution,expected", [("resolved", "completed"), ("cancelled", "failed")])
def test_resolution_survives_late_callbacks_and_does_not_adjudicate_comparison(lifecycle, resolution, expected):
    client, factory, _ = lifecycle
    cid, mid, rid = create(client)
    execution_event(client, cid, mid, rid, "response", "final",
                    payload={"contentText": "Proposta original aprovada ou recusada.", "reviewRequired": True})
    with factory() as db:
        comparison_ids = [run.id for run in db.scalars(select(RunModel).where(RunModel.message_id == mid))
                          if run.id != rid]
    complete(client, rid)
    for other in comparison_ids:
        complete(client, other)
    task = client.get("/reviews", headers=AUTH).json()["reviewTasks"][0]
    response = client.patch(f"/reviews/{task['id']}/resolve", headers=AUTH,
                            json={"status": resolution, "note": "Avaliacao encerrada", "resolvedBy": "Reviewer"})
    assert response.status_code == 200, response.text
    assert complete(client, rid)["status"] == expected
    execution_event(client, cid, mid, rid, "review", "required")
    execution_event(client, cid, mid, rid, "run", "started")
    for flag in (False, True):
        execution_event(client, cid, mid, rid, "response", "final",
                        payload={"contentText": "Callback atrasado não pode substituir o texto avaliado.", "reviewRequired": flag})
    execution_event(client, cid, mid, rid, "run", "failed")
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(ReviewTaskModel)) == 1
        assert db.get(ReviewTaskModel, UUID(task["id"])).status == resolution
        assert db.get(RunModel, rid).status == expected
        assert all(db.get(RunModel, other).status == "human_review_required" for other in comparison_ids)
        assert db.get(ConversationModel, cid).status == ("completed" if resolution == "resolved" else "error")
        inbound = db.get(MessageModel, mid)
        assert inbound.status == ("completed" if resolution == "resolved" else "error")
        assert inbound.metadata_json["reviewRequired"] is False
        outbound = db.scalar(select(MessageModel).where(MessageModel.conversation_id == cid,
                                                       MessageModel.direction == "outbound"))
        assert outbound.content_text == "Proposta original aprovada ou recusada."
    assert client.get("/reviews", headers=AUTH).json()["reviewTasks"] == []


def later_message(client, cid):
    response = client.post("/messages", headers=AUTH, data={"conversationId": str(cid),
        "text": "Qual o horario da farmacia?", "metadata_json": '{"architectureMode":"centralized_orchestration","runtimeMode":"real"}'})
    assert response.status_code == 202, response.text
    return UUID(response.json()["messageId"]), UUID(response.json()["runId"])


def test_older_open_review_keeps_conversation_pending_during_newer_run(lifecycle):
    client, factory, _ = lifecycle
    cid, mid, rid = create(client)
    complete(client, rid)
    later_mid, later_rid = later_message(client, cid)
    for family, name, payload in [
        ("run", "started", {}),
        ("response", "final", {"contentText": "Resposta simples.", "reviewRequired": False}),
        ("run", "completed", {"reviewRequired": False}),
        ("run", "failed", {}),
    ]:
        execution_event(client, cid, later_mid, later_rid, family, name, payload=payload)
        with factory() as db:
            assert db.get(ConversationModel, cid).status == "human_review_required"
            assert db.get(MessageModel, mid).status == "human_review_required"
    assert len(client.get("/reviews", headers=AUTH).json()["reviewTasks"]) == 1


def test_resolving_older_review_keeps_newer_active_work_waiting(lifecycle):
    client, factory, _ = lifecycle
    cid, mid, rid = create(client)
    complete(client, rid)
    later_mid, later_rid = later_message(client, cid)
    execution_event(client, cid, later_mid, later_rid, "run", "started")
    task = client.get("/reviews", headers=AUTH).json()["reviewTasks"][0]
    assert client.patch(f"/reviews/{task['id']}/resolve", headers=AUTH, json={"status": "resolved"}).status_code == 200
    with factory() as db:
        assert db.get(ConversationModel, cid).status == "waiting"
        assert db.get(MessageModel, later_mid).status == "processing"


def test_human_events_are_published_after_commit_and_duplicate_resolution_is_noop(lifecycle, monkeypatch):
    client, factory, _ = lifecycle
    cid, mid, rid = create(client)
    complete(client, rid)
    task = client.get("/reviews", headers=AUTH).json()["reviewTasks"][0]
    published = []
    def publish(event):
        with factory() as db:
            persisted = db.get(ReviewTaskModel, UUID(task["id"]))
            assert persisted.status == event.payload["resolutionStatus"]
        published.append(event)
    monkeypatch.setattr("app.services.reviews.event_bus.publish", publish)
    for status in ("in_review", "resolved", "resolved"):
        response = client.patch(f"/reviews/{task['id']}/resolve", headers=AUTH, json={"status": status})
        assert response.status_code == 200, response.text
    assert [event.payload["resolutionStatus"] for event in published] == ["in_review", "resolved"]
    assert all(event.payload["source"] == "human_review" for event in published)


def test_recovery_previews_without_writes_then_recovers_only_missing_canonical_tasks(lifecycle):
    client, factory, _ = lifecycle
    cid, mid, rid = create(client)
    resolved_cid, _, resolved_rid = create(client)
    other_cid, other_mid, _ = create(client)
    complete(client, resolved_rid)
    task = client.get("/reviews", headers=AUTH).json()["reviewTasks"][0]
    assert client.patch(f"/reviews/{task['id']}/resolve", headers=AUTH, json={"status": "resolved"}).status_code == 200
    with factory() as db:
        run = db.get(RunModel, rid)
        run.status, run.human_review_required = "human_review_required", True
        run.final_outcome = "human_review_required"
        comparison = next(run for run in db.scalars(select(RunModel).where(RunModel.message_id == other_mid))
                          if run.experiment_json.get("comparisonOnly"))
        comparison.status, comparison.human_review_required = "human_review_required", True
        # Legacy resolved canonical rows can retain flags; their task must win.
        old = db.get(RunModel, resolved_rid)
        old.status, old.human_review_required = "human_review_required", True
        db.commit()
        service = ReviewService(db)
        preview = service.reconcile_missing_review_tasks()
        assert preview["missingCount"] == 1
        assert preview["reviews"][0]["runId"] == str(rid)
        assert db.scalar(select(func.count()).select_from(ReviewTaskModel)) == 1
        assert service.reconcile_missing_review_tasks(apply=True)["missingCount"] == 1
        assert service.reconcile_missing_review_tasks(apply=True)["missingCount"] == 0
        assert db.scalar(select(func.count()).select_from(ReviewTaskModel)) == 2
        assert db.get(ConversationModel, cid).status == "human_review_required"
        assert db.get(ConversationModel, resolved_cid).status == "completed"
        assert db.get(ConversationModel, other_cid).status != "human_review_required"
