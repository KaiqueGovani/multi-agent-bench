"""Dashboard tool totals represent domain calls rather than lifecycle events."""
from types import SimpleNamespace

from app.services.dashboard import DashboardService


def event(name="started", *, tool="stock_lookup", run="run-1", actor="stock", call_id=None, kind=None, status=None):
    return SimpleNamespace(
        run_id=run, actor_name=actor, event_family="tool", event_name=name,
        tool_name=tool, status=status or ("running" if name == "started" else "completed"),
        payload_json={**({"toolCallId": call_id} if call_id else {}), **({"callKind": kind} if kind else {})},
    )


def distribution(events):
    return {item.key: item.count for item in DashboardService(None)._tool_distribution(events)}


def test_counts_each_identified_call_once_including_failed_and_inflight_calls():
    assert distribution([
        event(call_id="first"), event("completed", call_id="first"),
        event("completed", call_id="first"),  # Replayed duplicate lifecycle event.
        event(call_id="second"), event("failed", call_id="second", status="failed"),
        event(call_id="first", run="run-2"),
    ]) == {"stock_lookup": 3}


def test_excludes_specialist_wrappers_routing_and_peer_delegation():
    assert distribution([
        event(tool="RouteSelection", call_id="route"),
        event(tool="stock_specialist", call_id="delegate"),
        event(tool="handoff_to_peer", call_id="handoff"),
        event(tool="custom_wrapper", call_id="wrapper", kind="coordination"),
        event(tool="stock_lookup", call_id="lookup", kind="domain"),
    ]) == {"stock_lookup": 1}


def test_legacy_started_completed_and_lookup_logs_do_not_multiply_a_call():
    assert distribution([
        event(), event("stock.lookup"), event("completed"),
        event(), event("failed", status="failed"),
        event("faq.lookup", tool="faq_lookup", actor="faq"),
    ]) == {"stock_lookup": 2, "faq_lookup": 1}


def test_normalizes_tool_aliases_and_ignores_non_tool_events():
    ignored = event(call_id="not-tool")
    ignored.event_family = "agent"
    assert distribution([event(tool="Stock.Lookup", call_id="a"), event(tool="stock_lookup", call_id="b"), ignored]) == {"stock_lookup": 2}
