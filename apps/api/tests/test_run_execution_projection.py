"""Unit tests for active_actor_name / active_node_id clearing logic in _upsert_projection.

These tests verify the three-branch logic without requiring a real database.
We extract the logic into a helper and test it with plain objects.
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.services.run_execution as run_execution_module
from app.schemas.domain import RunExecutionEvent
from app.schemas.enums import ProcessingStatus
from app.services.run_execution import RunExecutionService


def _apply_active_actor_logic(event, projection):
    """Mirror the active_actor clearing logic from RunExecutionService._upsert_projection."""
    is_running = event.status == ProcessingStatus.RUNNING.value
    is_terminal_run = (
        event.event_family == "run"
        and event.event_name in ("completed", "failed")
    )
    is_actor_completing = (
        event.status == ProcessingStatus.COMPLETED.value
        and event.actor_name is not None
        and event.actor_name == projection.active_actor_name
    )
    if is_running and event.actor_name:
        projection.active_actor_name = event.actor_name
        projection.active_node_id = event.node_id
    elif is_terminal_run or is_actor_completing:
        projection.active_actor_name = None
        projection.active_node_id = None
    # else: leave as-is


def _make_projection(active_actor_name=None, active_node_id=None):
    return SimpleNamespace(
        active_actor_name=active_actor_name,
        active_node_id=active_node_id,
    )


def _make_event(event_family, event_name, status, actor_name=None, node_id=None):
    return SimpleNamespace(
        event_family=event_family,
        event_name=event_name,
        status=status,
        actor_name=actor_name,
        node_id=node_id,
    )


class TestActiveActorProjectionLogic:
    def test_running_event_sets_active_actor(self):
        proj = _make_projection()
        evt = _make_event("node", "started", "running", actor_name="faq_agent", node_id="n1")
        _apply_active_actor_logic(evt, proj)
        assert proj.active_actor_name == "faq_agent"
        assert proj.active_node_id == "n1"

    def test_run_completed_clears_active_actor(self):
        proj = _make_projection(active_actor_name="faq_agent", active_node_id="n1")
        evt = _make_event("run", "completed", "completed")
        _apply_active_actor_logic(evt, proj)
        assert proj.active_actor_name is None
        assert proj.active_node_id is None

    def test_run_failed_clears_active_actor(self):
        proj = _make_projection(active_actor_name="faq_agent", active_node_id="n1")
        evt = _make_event("run", "failed", "failed")
        _apply_active_actor_logic(evt, proj)
        assert proj.active_actor_name is None
        assert proj.active_node_id is None

    def test_actor_completing_clears_when_matches(self):
        proj = _make_projection(active_actor_name="response_streamer", active_node_id="rs.1")
        evt = _make_event("node", "completed", "completed", actor_name="response_streamer", node_id="rs.done")
        _apply_active_actor_logic(evt, proj)
        assert proj.active_actor_name is None
        assert proj.active_node_id is None

    def test_actor_completing_does_not_clear_when_different(self):
        proj = _make_projection(active_actor_name="supervisor_agent", active_node_id="sup.1")
        evt = _make_event("node", "completed", "completed", actor_name="faq_agent", node_id="faq.done")
        _apply_active_actor_logic(evt, proj)
        assert proj.active_actor_name == "supervisor_agent"
        assert proj.active_node_id == "sup.1"

    def test_completed_event_without_actor_leaves_as_is(self):
        proj = _make_projection(active_actor_name="faq_agent", active_node_id="n1")
        evt = _make_event("tool", "completed", "completed", actor_name=None)
        _apply_active_actor_logic(evt, proj)
        assert proj.active_actor_name == "faq_agent"
        assert proj.active_node_id == "n1"

    def test_running_event_without_actor_name_leaves_as_is(self):
        proj = _make_projection(active_actor_name="old", active_node_id="old.1")
        evt = _make_event("tool", "started", "running", actor_name=None, node_id="t.1")
        _apply_active_actor_logic(evt, proj)
        assert proj.active_actor_name == "old"
        assert proj.active_node_id == "old.1"


class TestRunExecutionPublicEvents:
    def test_comparison_only_event_still_derives_public_conversation_event(self, monkeypatch):
        service = RunExecutionService(_FakeDb())
        derived_events = []

        monkeypatch.setattr(service, "_next_sequence", lambda run_id: 1)
        monkeypatch.setattr(service, "_upsert_projection", lambda model: None)
        monkeypatch.setattr(service, "_is_comparison_only", lambda run_id: True)
        monkeypatch.setattr(service, "_sync_comparison_outbound", lambda model: None)
        monkeypatch.setattr(service, "_derive_public_event", lambda event: derived_events.append(event))
        monkeypatch.setattr(run_execution_module.run_execution_bus, "publish", lambda event: None)

        service.record_event(
            run_id=uuid4(),
            conversation_id=uuid4(),
            message_id=uuid4(),
            correlation_id=uuid4(),
            event_family="response",
            event_name="final",
            status=ProcessingStatus.COMPLETED,
            payload={"contentText": "Workflow response"},
        )

        assert len(derived_events) == 1
        assert derived_events[0].event_family == "response"
        assert derived_events[0].event_name == "final"

    def test_public_event_payload_includes_architecture_mode(self, monkeypatch):
        run_id = uuid4()
        db = _FakeDb(
            run=SimpleNamespace(
                experiment_json={"architectureKey": "structured_workflow"}
            )
        )
        service = RunExecutionService(db)
        recorded_events = []

        class FakeEventService:
            def __init__(self, db):
                self._db = db

            def record_event(self, **kwargs):
                recorded_events.append(kwargs)

        monkeypatch.setattr(run_execution_module, "EventService", FakeEventService)

        service._derive_public_event(
            RunExecutionEvent(
                id=uuid4(),
                run_id=run_id,
                conversation_id=uuid4(),
                message_id=uuid4(),
                correlation_id=uuid4(),
                event_family="response",
                event_name="partial",
                sequence_no=7,
                created_at=datetime.now(UTC),
                status=ProcessingStatus.RUNNING,
                actor_name="workflow_synthesis_agent",
                node_id="workflow_synthesis_agent.partial",
                source="ai_service",
                payload={"contentText": "partial"},
            )
        )

        assert recorded_events[0]["payload"]["architectureMode"] == "structured_workflow"
        assert recorded_events[0]["payload"]["runId"] == str(run_id)


class _FakeDb:
    def __init__(self, run=None):
        self.run = run

    def add(self, model):
        self.model = model

    def flush(self):
        pass

    def commit(self):
        pass

    def refresh(self, model):
        pass

    def get(self, model_type, model_id):
        if model_type is run_execution_module.RunModel:
            return self.run
        return None
