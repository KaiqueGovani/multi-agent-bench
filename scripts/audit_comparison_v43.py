#!/usr/bin/env python3
"""Audit v4.3 generation artifacts offline from metadata and frozen case inputs."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime
import hashlib
from itertools import permutations, product
import json
import os
from pathlib import Path
from uuid import UUID, uuid5

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "architectural-comparison-v4.3"
ARCHITECTURES = ("centralized_orchestration", "structured_workflow", "decentralized_swarm")
SPECIALIST_TOOLS = {"faq_specialist": "faq", "stock_specialist": "stock", "attachments_specialist": "attachments"}
DOMAIN_ROLES = {"faq_lookup": "faq", "stock_lookup": "stock", "attachment_intake": "attachments"}
ROLES = set(DOMAIN_ROLES.values())
TOKEN_FIELDS = {"input_tokens": "inputTokens", "output_tokens": "outputTokens", "total_tokens": "totalTokens"}
PLAN_FIELDS = ("unit_id", "scenario_id", "repetition", "architecture", "block", "position", "global_position", "randomization_seed")
TERMINAL_FIELDS = ("attempt_id", "run_id", "worker_pid", "status", "success", "architectural_compliance",
                   "comparison_protocol", "model_requests", "domain_tool_calls", "coordination_tool_calls",
                   "token_measurement_complete", *TOKEN_FIELDS)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_sha(data):
    return sha(json.dumps(data, sort_keys=True).encode())


def stamp(value):
    return datetime.fromisoformat(value)


class Audit:
    def __init__(self):
        self.issues = []
        self.position = None
        self.observations = Counter()
        self.ids = defaultdict(set)

    def check(self, condition, code, **metadata):
        if not condition:
            item = {"code": code, **metadata}
            if self.position is not None:
                item["unit_position"] = self.position
            self.issues.append(item)
        return bool(condition)

    def unique(self, namespace, value):
        self.check(bool(value) and value not in self.ids[namespace], "missing_or_reused_identity", namespace=namespace)
        if value:
            self.ids[namespace].add(value)

    def json(self, path):
        try:
            value = json.loads(path.read_text())
            if self.check(isinstance(value, dict), "invalid_json_object", artifact=path.name):
                return value
            return {}
        except (OSError, ValueError):
            self.check(False, "missing_or_invalid_artifact", artifact=path.name)
            return {}

    def jsonl(self, path):
        try:
            with path.open() as file:
                records = []
                for line, row in enumerate(file, 1):
                    try:
                        value = json.loads(row)
                        if self.check(isinstance(value, dict), "invalid_jsonl_object", artifact=path.name, line=line):
                            records.append(value)
                    except ValueError:
                        self.check(False, "invalid_jsonl_record", artifact=path.name, line=line)
                return records
        except OSError:
            self.check(False, "missing_or_invalid_artifact", artifact=path.name)
            return []


def triplet(unit):
    return unit["scenario_id"], unit["repetition"], unit["architecture"]


def inspect_plan(audit, folder, manifest):
    cases = {case["id"]: case for case in manifest["cases"]}
    order = manifest["order"]
    workers = manifest["generation_dispatch"]["workers"]
    repetitions = manifest["repetitions"]
    audit.check(manifest["configuration"]["protocol"] == PROTOCOL, "wrong_protocol")
    audit.check(json_sha(manifest["cases"]) == manifest["cases_sha256"], "manifest_case_hash_mismatch")
    audit.check(len(cases) == len(manifest["cases"]), "duplicate_manifest_case")
    expected = set(product(cases, range(repetitions), ARCHITECTURES))
    audit.check(len(order) == len(expected) and {triplet(u) for u in order} == expected, "planned_factorial_pairing_mismatch")
    audit.check(workers > 0 and workers % 3 == 0, "invalid_wave_size")
    csv_path = folder / "execution-order.csv"
    if csv_path.exists():
        with csv_path.open() as file:
            csv_order = list(csv.DictReader(file))
        audit.check([tuple(row.get(k) for k in PLAN_FIELDS) for row in csv_order]
                    == [tuple(str(unit[k]) for k in PLAN_FIELDS) for unit in order], "order_csv_differs_from_manifest")
    else:
        audit.check(False, "missing_order_csv")
    distribution = Counter()
    position_counts = Counter()
    experiment_id = UUID(manifest["experiment_id"])
    for offset in range(0, len(order), 3):
        block = order[offset:offset + 3]
        architecture_order = tuple(u["architecture"] for u in block)
        distribution[architecture_order] += 1
        audit.check(set(architecture_order) == set(ARCHITECTURES) and len({triplet(u)[:2] for u in block}) == 1,
                    "incomplete_scenario_repetition_triplet", block=offset // 3)
        for position, unit in enumerate(block):
            scenario, repetition, architecture = triplet(unit)
            position_counts[(architecture, position)] += 1
            audit.unique("planned_unit", unit["unit_id"])
            audit.check(unit["unit_id"] == str(uuid5(experiment_id, f"{scenario}:{repetition}:{architecture}")),
                        "planned_unit_identity_mismatch", order_position=offset + position)
            audit.check(unit["global_position"] == offset + position and unit["position"] == position
                        and unit["block"] == offset // 3 and unit["randomization_seed"] == 20261011,
                        "planned_position_mismatch", order_position=offset + position)
    counts = [distribution[order] for order in permutations(ARCHITECTURES)]
    audit.check(max(counts) - min(counts) <= 1, "unbalanced_triplet_permutations")
    for architecture in ARCHITECTURES:
        positions = [position_counts[(architecture, position)] for position in range(3)]
        audit.check(max(positions) - min(positions) <= 1, "unbalanced_architecture_positions", architecture=architecture)
    return cases, order, workers


def initial_hashes(case):
    """Independent reconstruction of the model-visible initial case prefix.

    The final Boolean is checked for consistency across the paired case runs.
    Trying its two legal values keeps the input audit separate from the regex policy.
    """
    latest = case.get("text") or ""
    turns = [f'{"inbound" if item["role"] == "customer" else "outbound"}: {item["text"] or ""}'
             for item in case.get("history", [])]
    turns.append("inbound: " + latest)
    descriptors = [{"attachmentId": f"attachment-{i}", "originalFilename": item["filename"],
                    "mimeType": item["mime_type"], "sizeBytes": item["size_bytes"]}
                   for i, item in enumerate(case.get("attachments", []), 1)]
    prefix = ("Histórico integral normalizado:\n" + "\n".join(turns) + "\nMensagem atual: " + latest
              + "\nDescritores de anexos: " + json.dumps(descriptors, ensure_ascii=False)
              + "\nEncaminhamento obrigatório pela política comum: ")
    return {sha((prefix + str(required).lower() + ".").encode()): required for required in (False, True)}


def split_trace(audit, events, row):
    starts, terminals = defaultdict(dict), defaultdict(dict)
    rules = {"agent": ("started", "callId"), "model": ("started", "callId"),
             "tool": ("started", "toolCallId"), "handoff": ("requested", "transferId")}
    active_model = None
    for index, event in enumerate(events, 1):
        family, name = event["eventFamily"], event["eventName"]
        audit.check(event["sequence"] == index and event["runId"] == row.get("run_id"), "event_sequence_or_run_mismatch")
        audit.unique("external_event", event.get("externalEventId"))
        if family not in rules:
            continue
        start_name, key = rules[family]
        if name not in (start_name, "completed", "failed"):
            continue
        call = event["payload"].get(key)
        bucket = starts[family] if name == start_name else terminals[family]
        audit.check(bool(call) and call not in bucket, "duplicate_or_missing_trace_identity", family=family, event=name)
        if name == start_name and family != "tool":
            audit.unique(family, call)
        bucket[call] = event
        if family == "model":
            if name == "started":
                audit.check(active_model is None, "concurrent_provider_requests_inside_attempt")
                active_model = call
            else:
                audit.check(active_model == call, "out_of_order_model_terminal")
                active_model = None
    for family in rules:
        audit.check(set(terminals[family]) <= set(starts[family]), "orphan_trace_terminal", family=family)
        missing = set(starts[family]) - set(terminals[family])
        if row.get("success"):
            audit.check(not missing, "trace_missing_terminal_on_technical_success", family=family)
        elif missing:
            audit.observations[f"open_{family}_events_on_failed_attempts"] += len(missing)
    return starts, terminals


def inspect_requests(audit, starts, terminals, row, config):
    calls = starts["model"]
    models_by_agent = defaultdict(list)
    summed = Counter()
    known = Counter()
    for call, start in calls.items():
        payload = start["payload"]
        parent = payload.get("agentInvocationId")
        agent = starts["agent"].get(parent)
        end = terminals["model"].get(call)
        agent_end = terminals["agent"].get(parent)
        audit.check(agent is not None and payload.get("parentCallId") == parent, "provider_call_missing_agent_parent")
        if agent is not None:
            audit.check(start["actorName"] == agent["actorName"] and payload.get("agentId") == agent["payload"].get("agentId")
                        and agent["sequence"] < start["sequence"], "provider_agent_identity_mismatch")
        if end is None:
            continue
        audit.check(end["sequence"] > start["sequence"] and end["actorName"] == start["actorName"]
                    and all(end["payload"].get(k) == payload.get(k) for k in ("agentInvocationId", "agentId", "parentCallId")),
                    "provider_start_end_linkage_mismatch")
        if agent_end is not None:
            audit.check(end["sequence"] < agent_end["sequence"], "provider_request_outside_agent_envelope")
        usage = end["payload"].get("usage")
        models_by_agent[parent].append(end)
        if isinstance(usage, dict):
            for field, key in TOKEN_FIELDS.items():
                value = usage.get(key)
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    summed[field] += value
                    known[field] += 1
                else:
                    audit.check(False, "invalid_provider_token_value", token_field=field)
            if all(k in usage and isinstance(usage[k], int) for k in TOKEN_FIELDS.values()):
                audit.check(usage["totalTokens"] == usage["inputTokens"] + usage["outputTokens"], "provider_token_sum_mismatch")
            provider_id = end["payload"].get("providerRequestId") or usage.get("providerRequestId")
            if provider_id:
                audit.unique("provider_request_id", provider_id)
    complete = bool(calls) and all(known[k] == len(calls) for k in TOKEN_FIELDS) and all(
        e["eventName"] == "completed" for e in terminals["model"].values())
    audit.check(row.get("token_measurement_complete") == complete, "token_coverage_flag_mismatch")
    audit.check(row.get("model_requests") == len(calls), "provider_call_count_mismatch")
    audit.check(len(calls) <= config["max_model_calls"], "model_call_limit_breached")
    for field in TOKEN_FIELDS:
        audit.check(row.get(field) == (summed[field] if complete else None), "execution_token_total_mismatch", token_field=field)
        audit.check(row.get("known_partial_" + field) == (summed[field] if known[field] else None),
                    "known_partial_token_total_mismatch", token_field=field)
    for aid, agent in starts["agent"].items():
        end = terminals["agent"].get(aid)
        if end is None or end["eventName"] != "completed":
            continue
        own = models_by_agent[aid]
        if own and all(isinstance(e["payload"].get("usage"), dict) and e["eventName"] == "completed" for e in own):
            audit.check(end["payload"].get("sdkOwnTotalTokens") == sum(e["payload"]["usage"].get("totalTokens", 0) for e in own),
                        "sdk_own_usage_does_not_reconcile")
    return models_by_agent, summed, complete


def inspect_tools(audit, starts, terminals, row, config):
    tools = starts["tool"]
    for tid, start in tools.items():
        payload = start["payload"]
        role, name = start["actorName"], start["toolName"]
        aid = payload.get("agentInvocationId")
        parent, parent_end = starts["agent"].get(aid), terminals["agent"].get(aid)
        end = terminals["tool"].get(tid)
        audit.check(parent is not None and parent["actorName"] == role and parent["sequence"] < start["sequence"]
                    and payload.get("parentCallId") == aid, "tool_agent_parent_mismatch")
        if name in DOMAIN_ROLES:
            audit.check(role == DOMAIN_ROLES[name] and payload.get("callKind") == "domain", "domain_tool_wrong_role")
        if end is not None:
            audit.check(end["sequence"] > start["sequence"] and end["actorName"] == role and end["toolName"] == name
                        and all(end["payload"].get(k) == payload.get(k) for k in ("agentInvocationId", "agentId", "parentCallId"))
                        and (parent_end is None or end["sequence"] < parent_end["sequence"]), "tool_start_end_linkage_mismatch")
    domain_count = sum(e["toolName"] in DOMAIN_ROLES for e in tools.values())
    audit.check(domain_count <= config["max_domain_tool_calls"], "domain_call_limit_breached")
    counts = {"domain_tool_calls": domain_count, "coordination_tool_calls": len(tools) - domain_count,
              "agent_invocations": len(starts["agent"]), "actual_agents": len({e["payload"].get("agentId") for e in starts["model"].values()}),
              "specialist_tool_invocations": sum(e["toolName"] in SPECIALIST_TOOLS for e in tools.values()),
              "peer_delegations": len(starts["handoff"])}
    for key, value in counts.items():
        audit.check(row.get(key) == value, "trace_counter_mismatch", counter=key)


def inspect_authority(audit, events, starts, terminals, models_by_agent, row, config, attachment_required):
    architecture = row["architecture"]
    agents = list(starts["agent"].values())
    specialists = [e for e in agents if e["actorName"] in ROLES]
    completed = []
    for e in specialists:
        aid = e["payload"]["callId"]
        end = terminals["agent"].get(aid)
        if end is not None and end["eventName"] == "completed" and any(
                model["eventName"] == "completed" for model in models_by_agent[aid]):
            completed.append(end)
    completed.sort(key=lambda e: e["sequence"])
    roles = [e["actorName"] for e in completed]
    attachments_completed = "attachments" in roles
    finals = [e for e in events if e["eventFamily"] == "response" and e["eventName"] == "final"]
    rejects = [e for e in events if e["eventFamily"] == "response" and e["eventName"] == "rejected"]
    contracts = [e for e in events if e["eventFamily"] == "architecture" and e["eventName"] == "contract"]
    audit.check(len(finals) <= 1 and len(rejects) <= 1 and not (finals and rejects), "multiple_or_conflicting_final_states")
    gate_passes = bool(completed) and (not attachment_required or attachments_completed)
    if row.get("success"):
        audit.check(len(contracts) == 1, "missing_or_duplicate_architecture_contract")
    if contracts:
        contract = contracts[0]["payload"]
        audit.check(contract.get("architecture") == architecture and contract.get("attachmentRequired") == attachment_required
                    and contract.get("attachmentSpecialistCompleted") == attachments_completed
                    and contract.get("completedSpecialistRoles") == roles and contract.get("observed") == len(roles)
                    and contract.get("compliant") == gate_passes, "runtime_architecture_contract_mismatch")
        audit.check(bool(finals) == gate_passes and bool(rejects) != gate_passes, "architecture_gate_response_mismatch")
    if finals:
        final = finals[0]
        audit.check(gate_passes and all(e["sequence"] < final["sequence"] for e in completed)
                    and (not contracts or contracts[0]["sequence"] < final["sequence"]), "response_accepted_before_specialist_gate")
        audit.check(final["payload"].get("finalActor") == final["actorName"]
                    and (not contracts or contracts[0]["payload"].get("finalActor") == final["actorName"]),
                    "final_authority_metadata_mismatch")
        audit.check(all(e["sequence"] < final["sequence"] for events_by_family in terminals.values() for e in events_by_family.values()),
                    "execution_continues_after_final")
        audit.check(row.get("architectural_compliance") is True, "accepted_final_but_reported_contract_failed")
    if rejects:
        audit.check(row.get("architectural_compliance") is False, "rejected_response_but_reported_compliant")
    if not agents:
        return
    if architecture == "centralized_orchestration":
        audit.check(agents[0]["actorName"] == "supervisor" and len(agents) == len(specialists) + 1,
                    "central_unexpected_authority")
        audit.check(len(specialists) <= config["max_supervisor_specialist_invocations"], "central_specialist_limit_breached")
        audit.check(not starts["handoff"], "central_peer_handoff")
        policy = [e for e in events if e["eventFamily"] == "architecture" and e["eventName"] == "first_tool_choice"]
        scope = config["supervisor_first_tool_scope"]["with_attachments" if attachment_required else "without_attachments"]
        audit.check(len(policy) == 1 and policy[0]["payload"].get("toolChoice") == {"any": {}}
                    and policy[0]["payload"].get("allowedTools") == scope, "central_first_tool_policy_mismatch")
        aid = agents[0]["payload"]["callId"]
        parent_models = [e for e in starts["model"].values() if e["payload"].get("agentInvocationId") == aid]
        delegation_starts = [e for e in starts["tool"].values() if e["toolName"] in SPECIALIST_TOOLS]
        if finals:
            audit.check(finals[0]["actorName"] == "supervisor", "central_final_not_supervisor")
            audit.check(len(parent_models) >= 2 and bool(delegation_starts)
                        and all(e["toolName"] in scope for e in delegation_starts if e["sequence"] < parent_models[1]["sequence"])
                        and delegation_starts[0]["sequence"] < parent_models[1]["sequence"], "central_first_request_did_not_delegate_in_scope")
        for child in specialists:
            child_payload = child["payload"]
            tid = child_payload.get("parentCallId")
            tool, tool_end = starts["tool"].get(tid), terminals["tool"].get(tid)
            child_end = terminals["agent"].get(child_payload["callId"])
            audit.check(tool is not None and tool["actorName"] == "supervisor" and tool["sequence"] < child["sequence"]
                        and SPECIALIST_TOOLS.get(tool["toolName"]) == child["actorName"]
                        and child_payload.get("parentAgentInvocationId") == aid, "central_child_linkage_mismatch")
            if child_end is not None and tool_end is not None:
                audit.check(child_end["sequence"] < tool_end["sequence"], "central_tool_return_precedes_child_completion")
    elif architecture == "structured_workflow":
        audit.check(agents[0]["actorName"] == "router" and not starts["handoff"], "workflow_unexpected_entry_or_peer")
        audit.check(all(e["payload"].get("inputSha256") == agents[0]["payload"].get("inputSha256") for e in specialists),
                    "workflow_specialist_input_differs_from_initial_context")
        if finals:
            audit.check(agents[-1]["actorName"] == finals[0]["actorName"] == "synthesizer"
                        and len(specialists) == len(agents) - 2, "workflow_unexpected_final_authority")
        for sender, recipient in zip(agents, agents[1:]):
            sender_end = terminals["agent"].get(sender["payload"]["callId"])
            audit.check(sender_end is not None and sender_end["sequence"] < recipient["sequence"], "workflow_stages_overlap")
    else:
        inspect_swarm(audit, agents, starts, terminals, finals, config, attachment_required)


def inspect_swarm(audit, agents, starts, terminals, finals, config, attachment_required):
    entry = "attachments" if attachment_required else "faq"
    audit.check(agents[0]["actorName"] == entry and agents[0]["payload"].get("parentCallId") is None,
                "swarm_entry_role_mismatch")
    audit.check(all(e["actorName"] in ROLES for e in agents), "non_specialist_in_swarm")
    requests = list(starts["handoff"].values())
    audit.check(len(requests) <= config["max_handoffs"], "swarm_handoff_limit_breached")
    if finals:
        audit.check(len(requests) == len(agents) - 1 and finals[0]["actorName"] == agents[-1]["actorName"],
                    "swarm_final_not_last_specialist")
        final_agent = terminals["agent"].get(agents[-1]["payload"]["callId"])
        audit.check(final_agent is not None and final_agent["eventName"] == "completed"
                    and final_agent["payload"].get("stopReason") != "tool_use", "swarm_final_agent_did_not_finish")
    for index, transfer in enumerate(requests):
        payload = transfer["payload"]
        tid, hid = payload.get("toolCallId"), payload.get("transferId")
        tool, tool_end = starts["tool"].get(tid), terminals["tool"].get(tid)
        audit.check(payload.get("invocationOrigin") == "specialist_tool" and payload.get("hop") == index + 1
                    and payload.get("from") in ROLES and payload.get("to") in ROLES
                    and payload.get("from") != payload.get("to"), "swarm_non_peer_or_invalid_transfer")
        audit.check(tool is not None and tool["toolName"] == "handoff_to_peer" and tool["sequence"] < transfer["sequence"]
                    and tool["actorName"] == payload.get("from")
                    and tool["payload"].get("input", {}).get("peer_name") == payload.get("to")
                    and tool["payload"].get("agentInvocationId") == payload.get("parentAgentInvocationId"),
                    "swarm_transfer_without_model_selected_tool")
        if index + 1 >= len(agents):
            if finals:
                audit.check(False, "swarm_final_with_unstarted_receiver")
            continue
        sender, receiver = agents[index:index + 2]
        sender_id, receiver_id = sender["payload"]["callId"], receiver["payload"]["callId"]
        sender_end, receiver_end = terminals["agent"].get(sender_id), terminals["agent"].get(receiver_id)
        transfer_end = terminals["handoff"].get(hid)
        audit.check(payload.get("from") == sender["actorName"] and payload.get("to") == receiver["actorName"]
                    and payload.get("parentAgentInvocationId") == sender_id
                    and receiver["payload"].get("parentCallId") == tid
                    and receiver["payload"].get("parentAgentInvocationId") == sender_id, "swarm_sender_receiver_linkage_mismatch")
        audit.check(tool_end is not None and tool_end["status"] == "completed" and sender_end is not None
                    and sender_end["payload"].get("stopReason") == "tool_use"
                    and transfer["sequence"] < tool_end["sequence"] < sender_end["sequence"] < receiver["sequence"],
                    "swarm_authority_transferred_without_sender_stop")
        if transfer_end is not None and transfer_end["eventName"] == "completed":
            audit.check(receiver_end is not None and receiver_end["sequence"] < transfer_end["sequence"]
                        and transfer_end["payload"].get("recipientAgentInvocationId") == receiver_id
                        and all(transfer_end["payload"].get(k) == payload.get(k) for k in ("from", "to", "toolCallId", "parentAgentInvocationId")),
                        "swarm_transfer_terminal_receiver_mismatch")


def audit_generation(folder):
    audit = Audit()
    manifest = audit.json(folder / "manifest.json")
    if not manifest:
        return {"passed": False, "anomalies": audit.issues}
    try:
        cases, order, workers = inspect_plan(audit, folder, manifest)
    except (KeyError, TypeError, ValueError) as error:
        audit.check(False, "invalid_manifest_structure", error_type=type(error).__name__)
        return {"passed": False, "anomalies": audit.issues}
    if workers <= 0:
        return {"passed": False, "anomalies": audit.issues}
    config = manifest["configuration"]
    drift = []
    for key, snapshot_directory in (("code_hashes", "code-snapshot"), ("asset_hashes", "assets-snapshot")):
        for name, expected in manifest[key].items():
            relative = Path(name)
            if not audit.check(not relative.is_absolute() and ".." not in relative.parts and relative.suffix in {".py", ".json", ".md"},
                               "invalid_frozen_snapshot_path", snapshot=snapshot_directory):
                continue
            saved = folder / snapshot_directory / name
            audit.check(saved.is_file() and sha(saved.read_bytes()) == expected, "frozen_snapshot_hash_mismatch", snapshot=snapshot_directory)
            if key == "code_hashes":
                live = ROOT / name
                if not live.is_file() or sha(live.read_bytes()) != expected:
                    drift.append(name)
    runs, journal = audit.jsonl(folder / "runs.jsonl"), audit.jsonl(folder / "attempts.jsonl")
    by_unit = {r.get("unit_id"): r for r in runs}
    by_attempt = {r.get("attempt_id"): r for r in journal}
    audit.check(len(by_unit) == len(runs) == len({r.get("attempt_id") for r in runs}), "duplicate_canonical_units_or_attempts")
    audit.check(len(by_attempt) == len(journal) == len({r.get("unit_id") for r in journal}), "duplicate_first_attempt_journal_entries")
    audit.check(set(by_unit) <= {u["unit_id"] for u in order}, "unplanned_canonical_unit")
    audit.check([r.get("unit_id") for r in runs] == [u["unit_id"] for u in order if u["unit_id"] in by_unit],
                "terminal_export_order_differs_from_plan")
    audit.check(len(journal) == len(runs) and set(by_attempt) == {r.get("attempt_id") for r in runs}, "canonical_attempt_journal_mismatch")
    audit.check(len(runs) == len(order), "planned_units_without_terminal_export", terminal=len(runs), planned=len(order))
    audited_inputs = defaultdict(set)
    resources = defaultdict(Counter)
    wave_launches, wave_finishes = defaultdict(list), defaultdict(list)
    for unit in order:
        audit.position = unit["global_position"]
        uid = unit["unit_id"]
        row = by_unit.get(uid)
        if row is None:
            continue
        try:
            attempt = row.get("attempt_id")
            audit.unique("attempt", attempt)
            if row.get("run_id"):
                audit.unique("run", row["run_id"])
            case = cases[unit["scenario_id"]]
            directory = folder / uid
            task, launch, result = (audit.json(directory / filename) for filename in ("task.json", "launch.json", "result.json"))
            audit.check(task.get("case") == case and task.get("unit") == unit and task.get("experiment_id") == manifest["experiment_id"]
                        and task.get("protocol") == PROTOCOL and task.get("settings") == manifest["settings"], "attempt_input_differs_from_frozen_manifest")
            ids = (task.get("attempt_id"), launch.get("attempt_id"), result.get("attempt_id"), by_attempt.get(attempt, {}).get("attempt_id"))
            audit.check(all(i == attempt for i in ids), "durable_attempt_identity_mismatch")
            audit.check(all(row.get(k) == unit[k] and result.get(k) == unit[k] and by_attempt.get(attempt, {}).get(k) == unit[k]
                            for k in PLAN_FIELDS), "attempt_plan_identity_mismatch")
            audit.check(all(row.get(k) == result.get(k) == by_attempt.get(attempt, {}).get(k) for k in TERMINAL_FIELDS),
                        "terminal_metadata_disagrees_across_exports")
            if (directory / "started.json").exists():
                started = audit.json(directory / "started.json")
                audit.check(started.get("attempt_id") == attempt and started.get("run_id") == row.get("run_id")
                            and started.get("worker_pid") == launch.get("pid") == row.get("worker_pid"), "worker_start_identity_mismatch")
            elif row.get("success"):
                audit.check(False, "technical_success_without_worker_start")
            wave = audit.position // workers + 1
            size = min(workers, len(order) - (wave - 1) * workers)
            audit.check(launch.get("wave") == row.get("generation_wave") == wave
                        and launch.get("wave_size") == row.get("generation_wave_size") == size, "wave_admission_identity_mismatch")
            if launch.get("started_at"):
                wave_launches[wave].append(stamp(launch["started_at"]))
            if row.get("finished_at"):
                wave_finishes[wave].append(stamp(row["finished_at"]))
            if launch.get("started_at") and row.get("started_at") and row.get("finished_at"):
                audit.check(stamp(launch["started_at"]) <= stamp(row["started_at"]) <= stamp(row["finished_at"]), "invalid_attempt_clock_order")
            if row.get("success") and row.get("latency_ms") is not None:
                audit.check(row["latency_ms"] <= config["timeout_seconds"] * 1000, "technical_success_after_core_deadline")
            events_path = directory / "events.jsonl"
            events = audit.jsonl(events_path) if events_path.exists() or row.get("success") else []
            config_events = [e for e in events if (e["eventFamily"], e["eventName"]) == ("experiment", "configuration")]
            if config_events or row.get("success"):
                audit.check(len(config_events) == 1 and config_events[0]["payload"] == config
                            and config.get("sources_profile") == "controlled-research", "effective_runtime_configuration_mismatch")
            starts, terminals = split_trace(audit, events, row)
            agents = list(starts["agent"].values())
            if agents:
                actual = agents[0]["payload"].get("inputSha256")
                expected_hashes = initial_hashes(case)
                audit.check(actual in expected_hashes, "initial_agent_input_hash_mismatch")
                for final in (e for e in events if e["eventFamily"] == "response" and e["eventName"] == "final"):
                    audit.check(actual in expected_hashes and final["payload"].get("reviewRequired") == expected_hashes[actual],
                                "final_referral_flag_differs_from_initial_context")
                audited_inputs[unit["scenario_id"]].add(actual)
                for instance in {e["payload"].get("agentId") for e in agents}:
                    audit.unique("agent_instance", instance)
            models_by_agent, tokens, complete = inspect_requests(audit, starts, terminals, row, config)
            inspect_tools(audit, starts, terminals, row, config)
            inspect_authority(audit, events, starts, terminals, models_by_agent, row, config, bool(case.get("attachments")))
            bucket = resources[unit["architecture"]]
            bucket.update({"terminal_units": 1, "technical_successes": bool(row.get("success")),
                           "architectural_compliant": row.get("architectural_compliance") is True,
                           "token_usage_complete_units": complete, "physical_requests_started": len(starts["model"]),
                           "physical_requests_terminal": len(terminals["model"]), "attachment_cases": bool(case.get("attachments")),
                           "accepted_peer_handoffs": len(starts["handoff"]), **{"known_" + k: v for k, v in tokens.items()}})
            if not row.get("success"):
                audit.observations["technical_failures_preserved"] += 1
            if row.get("architectural_compliance") is False:
                audit.observations["architecture_contract_failures_preserved"] += 1
        except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
            audit.check(False, "invalid_unit_artifact_schema", error_type=type(error).__name__)
            audit.observations["units_with_unreadable_trace_metadata"] += 1
    audit.position = None
    audit.check(all(len(hashes) == 1 for hashes in audited_inputs.values()), "paired_case_prompt_hash_disagreement")
    for wave in range(2, (len(order) + workers - 1) // workers + 1):
        if wave_launches[wave] and wave_finishes[wave - 1]:
            audit.check(min(wave_launches[wave]) >= max(wave_finishes[wave - 1]), "wave_started_before_previous_finished", wave=wave)
    return {
        "version": "comparison-v43-generation-audit-v1", "passed": not audit.issues,
        "audit_source_sha256": sha(Path(__file__).read_bytes()),
        "protocol": PROTOCOL, "planned_units": len(order), "terminal_units": len(runs), "paired_cases": len(cases),
        "case_input_hashes_verified": len(audited_inputs), "wave_workers": workers,
        "waves_with_launch_records": sum(bool(v) for v in wave_launches.values()),
        "frozen_snapshot_sources": len(manifest["code_hashes"]), "working_tree_source_drift_paths": sorted(drift),
        "working_tree_drift_note": "Frozen snapshots are the reference for historical traces. Current source drift is listed separately.",
        "architecture_resources": {name: dict(counts) for name, counts in resources.items()},
        "provider_identity_note": "Physical calls are counted by their unique runtime provider-call IDs. Upstream request IDs are verified only when present.",
        "upstream_provider_ids_observed": len(audit.ids["provider_request_id"]),
        "observations": dict(audit.observations), "anomalies": audit.issues,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cohort", type=Path)
    parser.add_argument("--output", type=Path, help="Optional restricted report path")
    args = parser.parse_args()
    report = audit_generation(args.cohort.resolve())
    data = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w") as output:
            output.write(data)
    print(data, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
