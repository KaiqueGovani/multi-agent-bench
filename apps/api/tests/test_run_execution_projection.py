"""Unit tests for active_actor_name / active_node_id clearing logic in _upsert_projection.

These tests verify the three-branch logic without requiring a real database.
We extract the logic into a helper and test it with plain objects.
"""

from types import SimpleNamespace

import pytest

from app.schemas.enums import ProcessingStatus


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
