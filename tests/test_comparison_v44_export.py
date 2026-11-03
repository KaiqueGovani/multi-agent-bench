"""Exercise the 600-row sanitized export with explicitly synthetic local records."""
import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze_comparison_v44 as exporter


class V44ExportTests(unittest.TestCase):
    def test_scope_rejection_is_distinct_from_verified_rejected_candidate(self):
        runs = {"one": {"attempt_id": "first", "architecture": exporter.ARCHES[0], "success": True,
                        "final_outcome": "architectural_contract_failed", "candidate_text": "synthetic candidate",
                        "architectural_compliance": False},
                "two": {"attempt_id": "second", "architecture": exporter.ARCHES[0], "success": True,
                        "final_outcome": "answered", "architectural_compliance": True}}
        violations = ["synthetic_contract_failure"]
        events = [
            {"attempt_id": "first", "eventFamily": "tool", "eventName": "rejected", "actorName": "supervisor",
             "status": "failed", "payload": {"toolCallId": "same-id", "reason": "outside_supervisor_turn_scope"}},
            {"attempt_id": "first", "eventFamily": "architecture", "eventName": "contract",
             "payload": {"compliant": False, "violations": violations, "scopeRejectedToolRequests": 1}},
            {"attempt_id": "first", "eventFamily": "response", "eventName": "rejected", "actorName": "supervisor",
             "status": "failed", "payload": {"candidateText": "synthetic candidate", "violations": violations,
                                               "architectureMode": exporter.ARCHES[0]}},
            {"attempt_id": "second", "eventFamily": "tool", "eventName": "started", "payload": {"toolCallId": "same-id"}},
        ]
        checked = exporter.audit_scope_events(events, runs)
        self.assertEqual(checked["first"], {"scope_rejected_tool_requests": 1, "architectural_candidate_rejected": True})
        self.assertEqual(checked["second"], {"scope_rejected_tool_requests": 0, "architectural_candidate_rejected": False})
        by_attempt = {row["attempt_id"]: row for row in runs.values()}
        accepted = exporter.summarize_trace_issues([{"attempt_id": "first", "reason": "missing terminal final event"}], by_attempt, checked)
        self.assertEqual(accepted["verified_architectural_candidate_rejections_without_final"], 1)
        with self.assertRaisesRegex(ValueError, "structural integrity"):
            exporter.summarize_trace_issues([{"attempt_id": "second", "reason": "missing terminal final event"}], by_attempt, checked)
        with self.assertRaisesRegex(ValueError, "also appears in a tool start"):
            exporter.audit_scope_events(events + [{**events[-1], "attempt_id": "first"}], runs)
        with self.assertRaisesRegex(ValueError, "without a final response"):
            exporter.audit_scope_events(events + [{"attempt_id": "first", "eventFamily": "response", "eventName": "final"}], runs)

    def test_parallel_audit_checks_complete_triplets_and_wave_barrier(self):
        with TemporaryDirectory(prefix="synthetic-v44-waves-") as temporary:
            cohort = Path(temporary)
            started = datetime(2027, 1, 1, tzinfo=timezone.utc)
            order = [{"unit_id": f"synthetic-unit-{index}-{arch}", "scenario_id": f"synthetic-{index}",
                      "repetition": 0, "architecture": arch} for index in range(3) for arch in exporter.ARCHES]
            manifest = {"created_at": started.isoformat(), "order": order,
                        "generation_dispatch": {"mode": exporter.PARALLEL_DISPATCH, "workers": 6}}
            runs = {}
            for index, unit in enumerate(order):
                wave = index // 6 + 1
                size = 6 if wave == 1 else 3
                launch_time = started + timedelta(seconds=2*wave, milliseconds=index % 6)
                uid = unit["unit_id"]
                directory = cohort / uid
                directory.mkdir()
                launch = {"attempt_id": f"synthetic-attempt-{index}", "started_at": launch_time.isoformat(),
                          "wave": wave, "wave_size": size}
                (directory / "launch.json").write_text(json.dumps(launch), encoding="utf-8")
                runs[uid] = {**unit, "attempt_id": launch["attempt_id"], "started_at": launch["started_at"],
                             "finished_at": (launch_time + timedelta(milliseconds=500)).isoformat(), "mode": "live",
                             "comparison_protocol": exporter.PROTOCOL, "generation_wave": wave, "generation_wave_size": size,
                             "end_to_end_latency_ms": 600}
            result = exporter.verify_generation(cohort, manifest, runs)
            self.assertEqual((result["waves"], result["wave_barriers_verified"], result["unit_timestamp_pairs_verified"]), (2, 1, 9))
            first = runs[order[0]["unit_id"]]
            first["collector_finished_at"] = (started + timedelta(seconds=5)).isoformat()
            with self.assertRaisesRegex(ValueError, "barrier"):
                exporter.verify_generation(cohort, manifest, runs)
            first.pop("collector_finished_at")
            first["generation_wave_size"] = 3
            with self.assertRaisesRegex(ValueError, "launch and terminal"):
                exporter.verify_generation(cohort, manifest, runs)

    def test_full_matrix_retains_unknowns_and_archives_only_sanitized_rows(self):
        with TemporaryDirectory(prefix="synthetic-v44-test-") as temporary:
            root = Path(temporary)
            cohort = root / "cohort"
            cohort.mkdir()
            original, manifest = self.prepare(cohort)
            output = root / "results"
            result = exporter.export(cohort, output, original, exporter.DEFAULT_PRICING, None, cohort / "engineering-gate.json")
            self.assertEqual(result["generated"], 600)
            self.assertEqual(result["responses_available"], 599)
            self.assertEqual(result["primary_schema_valid"], 598)
            self.assertEqual(result["primary_invalid_or_missing"], 1)
            self.assertEqual(result["task_unknown"], 1)
            self.assertEqual(result["human_validation_status"], "pending")
            self.assertEqual(result["recheck"]["schema_valid_rechecks"], 15)
            self.assertEqual(result["scope_probe"]["physical_requests"], 4)
            self.assertIsNone(exporter.read_json(output / "resource-consumption.json")["generation"]["estimated_cost_usd"])
            self.assertEqual({row["paired_scenarios"] for row in result["paired_success"]}, {40})
            self.assertEqual(result["provenance"]["judge_timestamp_pairs_checked"], 614)
            archive_path = root / "writer.zip"
            exporter.writer_zip(output, archive_path)
            with ZipFile(archive_path) as archive:
                self.assertIsNone(archive.testzip())
                names = archive.namelist()
                self.assertEqual(len(names), len(set(names)))
                self.assertIn("LEIA-ME.md", names)
                self.assertFalse(any("private" in name or "reviewer" in name for name in names))
                self.assertIn("research-data/results/architectural-comparison-v44/scope-probe-summary.json", names)
                csv_path = "research-data/results/architectural-comparison-v44/units.csv"
                sanitized = list(csv.DictReader(archive.read(csv_path).decode().splitlines()))
                self.assertEqual(len(sanitized), 600)
                self.assertEqual(len({(row["scenario_id"], row["architecture"], row["repetition"]) for row in sanitized}), 600)
                self.assertEqual(sum(int(row["scope_rejected_tool_requests"]) for row in sanitized), 1)
                self.assertFalse(any("SYNTHETIC PRIVATE RESPONSE" in archive.read(name).decode(errors="ignore") for name in names))
            manifest["order"] = manifest["order"][1:]
            with self.assertRaisesRegex(ValueError, "600 distinct"):
                exporter.validate_plan(manifest, exporter.read_json(original))

    def test_full_parallel_export_reports_amendment_and_frozen_dispatch(self):
        with TemporaryDirectory(prefix="synthetic-v44-parallel-") as temporary:
            root = Path(temporary)
            cohort = root / "cohort"
            cohort.mkdir()
            original, manifest = self.prepare(cohort)
            manifest["generation_dispatch"] = {"mode": exporter.PARALLEL_DISPATCH, "workers": 48}
            manifest["evaluation_plan"]["dispatch_workers"] = 48
            manifest["analysis_plan"]["parallel_amendment"] = {
                "requested_by_author_before_parallel_cohort": True, "previous_sequential_terminal_units": 54,
                "previous_sequential_evaluations": 0, "reuse_previous_first_attempts": False,
            }
            manifest["analysis_plan_sha256"] = exporter.canonical_digest(manifest["analysis_plan"])
            path = cohort / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            manifest_hash = exporter.digest(path)
            gate = cohort / "engineering-gate.json"
            gate.write_text(json.dumps({"passed": True, "main_manifest_sha256": manifest_hash}), encoding="utf-8")
            for name in ("runs.jsonl", "attempts.jsonl", "aggregated-evaluations.jsonl"):
                path = cohort / name
                rows = exporter.read_jsonl(path)
                for index, row in enumerate(rows):
                    wave, size = index // 48 + 1, 24 if index >= 576 else 48
                    row.update(generation_wave=wave, generation_wave_size=size)
                    if name == "runs.jsonl":
                        directory = cohort / row["unit_id"]
                        directory.mkdir()
                        launch = {"attempt_id": row["attempt_id"], "started_at": row["started_at"], "wave": wave, "wave_size": size}
                        (directory / "launch.json").write_text(json.dumps(launch), encoding="utf-8")
                path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            blind = cohort / "blind-responses.json"
            blind.write_text("[]", encoding="utf-8")
            for phase, planned in (("primary", 599), ("recheck", 15)):
                folder = cohort / "parallel-judging" / phase
                folder.mkdir(parents=True)
                (folder / "dispatch.json").write_text(json.dumps({"workers": 48, "manifest_sha256": manifest_hash,
                    "configuration_sha256": manifest["evaluation_plan"]["configuration_sha256"],
                    "blind_responses_sha256": exporter.digest(blind), "planned_blind_responses": planned}), encoding="utf-8")
                (folder / "summary.json").write_text(json.dumps({"unstarted_remaining": 0}), encoding="utf-8")
            output = root / "parallel-results"
            result = exporter.export(cohort, output, original, exporter.DEFAULT_PRICING, None, gate)
            provenance = result["provenance"]
            self.assertEqual(provenance["execution"], "parallel_balanced_waves")
            self.assertEqual(provenance["judge_workers"], 48)
            self.assertEqual(provenance["generation_dispatch"]["wave_barriers_verified"], 12)
            report = (output / "RELATORIO.md").read_text(encoding="utf-8")
            self.assertIn("48 processos em 13 ondas", report)
            self.assertIn("lote sequencial anterior terminou com 54", report)

    def prepare(self, cohort):
        start = datetime(2027, 1, 1, tzinfo=timezone.utc)

        def json_file(name, value):
            (cohort / name).write_text(json.dumps(value), encoding="utf-8")

        def json_lines(name, rows):
            (cohort / name).write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

        plan = exporter.read_json(exporter.ROOT / "experiments/architectural-comparison-v42/analysis-plan.json")
        cases = [{"id": f"synthetic-{i:02}", "stratum": ("faq", "stock", "attachments", "continuity", "professional_review")[i % 5],
                  "difficulty": ("low", "medium", "high")[i % 3]} for i in range(40)]
        combinations = [(case, rep, arch) for case in cases for rep in range(5) for arch in exporter.ARCHES]
        units = [dict(unit_id=f"synthetic-u{i:03}", scenario_id=case["id"], architecture=arch, repetition=rep)
                 for i, (case, rep, arch) in enumerate(combinations)]
        config = {"model_id": "us.anthropic.claude-haiku-4-5-20251001-v1:0", "region": "us-west-2",
                  "sources_profile": "controlled-research", "workflow_and_swarm_core": "architectural-comparison-v4.2"}
        judge = {"model_id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0", "region": "us-west-2"}
        judge_plan = {"configuration_sha256": exporter.canonical_digest(judge), "model_id": judge["model_id"],
                      "temperature": 0, "max_tokens": 4096, "version": "synthetic-test", "dispatch_workers": 1}
        historical = {"experiment_id": "historical-synthetic", "cases": cases, "cases_sha256": "synthetic-test",
                      "configuration": config, "analysis_plan": plan, "evaluation_plan": judge_plan, "order": units}
        original = cohort.parent / "historical-synthetic.json"
        original.write_text(json.dumps(historical), encoding="utf-8")
        new_plan = {**plan, "version": "synthetic-test-v44"}
        manifest = {**historical, "configuration": {**config, "protocol": exporter.PROTOCOL}, "experiment_id": "new-synthetic",
                    "created_at": start.isoformat(), "analysis_plan": new_plan, "analysis_plan_sha256": exporter.canonical_digest(new_plan),
                    "repetitions": 5, "dataset_version": "synthetic-test", "generation_dispatch": {"workers": 1, "mode": "sequential"},
                    "stability_recheck_plan": {"unit_ids": [unit["unit_id"] for unit in units[10:25]]}}
        json_file("manifest.json", manifest)
        json_file("engineering-gate.json", {"passed": True, "main_manifest_sha256": exporter.digest(cohort / "manifest.json")})
        json_file("judge-config.json", judge)
        runs, aggregates, events, judge_events, evaluations, failures, rechecks, changes = ([] for _ in range(8))
        mapping = {}
        usage = {"inputTokens": 100, "outputTokens": 20, "totalTokens": 120}
        for i, unit in enumerate(units):
            attempt = f"synthetic-attempt-{i}"
            rid = f"synthetic-rid-{i}"
            success = i != 0
            run = {**unit, "attempt_id": attempt, "mode": "live", "comparison_protocol": exporter.PROTOCOL,
                   "started_at": (start + timedelta(seconds=2*i)).isoformat(), "finished_at": (start + timedelta(seconds=2*i+1)).isoformat(),
                   "final_text": "SYNTHETIC PRIVATE RESPONSE" if success else "", "status": "completed" if success else "timeout",
                   "success": success, "architectural_compliance": True if success else None, "token_measurement_complete": success,
                   "model_requests": 1, "input_tokens": 100 if success else None, "output_tokens": 20 if success else None,
                   "total_tokens": 120 if success else None, "latency_ms": 1000 if success else None, "end_to_end_latency_ms": 1500}
            runs.append(run)
            task = None if i == 1 else i % 7 != 0 and success
            evaluation = {"criteria": [{"met": task}], "critical_violations": [], "evidence_insufficient": False,
                          "quality": dict.fromkeys(exporter.DIMS, 4)} if success and i != 1 else None
            aggregates.append({**run, "response_id": rid if success else None, "evaluation": evaluation, "task_success": task,
                               "procedure_applicable": False, "procedure_compliance": None,
                               "objective_checks": {"critical_violations": [], "required_evidence": []}})
            for state in ("started", "completed") if success else ("started",):
                events.append({"attempt_id": attempt, "eventFamily": "model", "eventName": state,
                               "payload": {"callId": f"synthetic-call-{i}", "usage": usage if state == "completed" else None}})
            if i == 3:
                events.append({"attempt_id": attempt, "eventFamily": "tool", "eventName": "rejected", "status": "failed",
                               "actorName": "supervisor", "payload": {"toolCallId": "synthetic-scope-rejected",
                                                                         "reason": "outside_supervisor_turn_scope"}})
            if not success:
                continue
            mapping[rid] = attempt
            for phase in ("primary", "recheck") if 10 <= i < 25 else ("primary",):
                request = f"synthetic-judge-{phase}-{i}"
                started = start + timedelta(seconds=(1300 if phase == "primary" else 2300) + i)
                event = {"phase": phase, "attempt_id": request, "response_id": rid, "format_repair": 0, "started_at": started.isoformat()}
                judge_events.extend([{**event, "event": "started"}, {**event, "event": "completed", "valid": evaluation is not None,
                                     "usage": {**usage, "providerRequestId": request}, "latency_ms": 5}])
                record = {"response_id": rid, "attempt_id": request, "evaluation": evaluation}
                if phase == "recheck":
                    rechecks.append(record)
                    changes.append({"response_id": rid, "primary_evaluation_available": True, "repeat_evaluation_available": True,
                                    "task_success_first": task, "task_success_second": task, "classification_changed": False,
                                    "critical_comparison_evaluable": True, "critical_disagreement": False})
                elif evaluation is None:
                    failures.append({"phase": phase, "response_id": rid, "attempt_id": request})
                else:
                    evaluations.append(record)
        for name, rows in (("runs", runs), ("attempts", runs), ("aggregated-evaluations", aggregates), ("events", events),
                           ("judge-attempts", sorted(judge_events, key=lambda row: row["phase"] != "primary")), ("evaluations", evaluations),
                           ("evaluation-failures", failures), ("reevaluations", rechecks)):
            json_lines(name + ".jsonl", rows)
        json_file("blind-mapping.json", mapping)
        json_file("recheck-selection.json", {"response_ids": [row["response_id"] for row in rechecks]})
        json_file("recheck-analysis.json", {"planned": 15, "changes": changes})
        json_file("readiness.json", {"attempts": 600, "calibration_passed": True,
                                     "integrity_issues": [{"attempt_id": runs[0]["attempt_id"], "reason": "model unresolved IDs"}]})
        json_file("../scope-probe-summary.json", {"scope": "separate synthetic engineering probe", "contract_passed": True,
                                                 "out_of_scope_requests_rejected": 1, "rejected_request_execution_count": 0,
                                                 "physical_requests": 4, "input_tokens": 500, "output_tokens": 100})
        return original, manifest


if __name__ == "__main__":
    unittest.main()
