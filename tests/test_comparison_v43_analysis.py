"""Offline checks using fabricated scenarios and scores with no real reviewer claims."""
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_comparison_v43 as analysis
import human_review_v43 as review


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def write_lines(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


class V43AnalysisTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory(prefix="synthetic-v43-test-")
        self.addCleanup(directory.cleanup)
        self.cohort = Path(directory.name)
        plan = review.read_json(ROOT / "experiments/architectural-comparison-v43/analysis-plan.json")
        cases = [{"id": f"synthetic-{stratum}-{index}", "stratum": stratum,
                  "text": "Solicitação sintética", "history": [{"role": "user", "text": "Contexto sintético"}],
                  "attachments": [], "intent": "teste", "expected_facts": [], "unsupported_claims": [],
                  "prohibited_behaviors": [], "essential_requirements": [{"criterion_id": "C1", "rule": "Teste"}],
                  "professional_review_required": stratum == "professional_review", "critical_restrictions": [],
                  "required_evidence": []} for stratum in plan["human_sample"]["strata"] for index in range(2)]
        units = [{"unit_id": f"test-{case['id']}-{arch}-{repeat}", "scenario_id": case["id"], "stratum": case["stratum"],
                  "architecture": arch, "repetition": repeat} for case in cases for arch in review.ARCHITECTURES for repeat in range(2)]
        self.manifest = {"configuration": {"protocol": review.PROTOCOL, "region": "us-west-2", "model_id": analysis.MODELS["generation"]},
                         "evaluation_plan": {"model_id": analysis.MODELS["judge"]}, "repetitions": 2, "cases": cases, "order": units,
                         "analysis_plan": plan, "analysis_plan_sha256": review.canonical_digest(plan),
                         "generation_dispatch": {"workers": 6, "mode": "mixed-test"}, "measurement_boundaries": {}}
        write_json(self.cohort / "manifest.json", self.manifest)
        self.cases = {case["id"]: case for case in cases}
        self.units = {unit["unit_id"]: unit for unit in units}
        self.sample = review.select_sample(self.manifest, self.cases, self.units)

    def write_artifacts(self):
        missing = self.sample[0]
        runs = []
        aggregates = []
        model_events = []
        mapping = {}
        usage = {"inputTokens": 100, "outputTokens": 20, "totalTokens": 120}
        for index, (uid, unit) in enumerate(self.units.items()):
            final = "" if uid == missing else "Resposta sintética com rótulo workflow estruturado."
            rid = f"blind-{index}" if final else None
            run = {**unit, "attempt_id": f"run-{index}", "final_text": final, "model_requests": 1,
                   "token_measurement_complete": bool(final), "input_tokens": 100 if final else None,
                   "output_tokens": 20 if final else None, "total_tokens": 120 if final else None,
                   "success": bool(final), "architectural_compliance": False, "latency_ms": index if final else None,
                   "end_to_end_latency_ms": index + 10}
            runs.append(run)
            if rid:
                mapping[rid] = run["attempt_id"]
            evaluation = {"criteria": [{"criterion_id": "C1", "met": True}], "critical_violations": [],
                          "referral_recommendation_observed": True, "evidence_insufficient": False,
                          "quality": dict.fromkeys(analysis.QUALITY_DIMENSIONS, 5)} if final else None
            aggregates.append({**run, "response_id": rid, "evaluation": evaluation, "procedure_applicable": False,
                               "objective_checks": {"critical_violations": []}})
            for state in ("started", "completed" if final else "failed"):
                model_events.append({"attempt_id": run["attempt_id"], "eventFamily": "model", "eventName": state,
                                     "payload": {"callId": f"model-{index}", "usage": usage if final and state == "completed" else None}})
        write_lines(self.cohort / "runs.jsonl", runs)
        write_lines(self.cohort / "aggregated-evaluations.jsonl", aggregates)
        write_lines(self.cohort / "events.jsonl", model_events)
        write_json(self.cohort / "blind-mapping.json", mapping)
        response, attempt = next(iter(mapping.items()))
        judge_arch = next(row["architecture"] for row in runs if row["attempt_id"] == attempt)
        write_lines(self.cohort / "judge-attempts.jsonl", [
            {"phase": "primary", "response_id": response, "attempt_id": f"judge-{index}", "event": state,
             "usage": {**usage, "providerRequestId": f"synthetic-provider-{index}"} if state == "completed" else None}
            for index in range(2) for state in ("started", "completed")])
        status = self.cohort / "parallel-judging" / "primary"
        status.mkdir(parents=True)
        write_json(status / "summary.json", {"unstarted_remaining": 0, "workers": 6})
        return judge_arch

    def test_sample_is_frozen_and_pairs_architectures_before_generation(self):
        self.assertEqual(review.freeze_sample(self.cohort), 30)
        for start in range(0, len(self.sample), 3):
            block = [self.units[uid] for uid in self.sample[start:start + 3]]
            self.assertEqual([row["architecture"] for row in block], list(review.ARCHITECTURES))
            self.assertEqual(len({(row["scenario_id"], row["repetition"]) for row in block}), 1)
        self.assertEqual(Counter(self.units[uid]["stratum"] for uid in self.sample),
                         dict.fromkeys(self.manifest["analysis_plan"]["human_sample"]["strata"], 6))
        with self.assertRaises(FileExistsError):
            review.freeze_sample(self.cohort)
        (self.cohort / "generation.lock").touch()
        with self.assertRaisesRegex(ValueError, "before generation"):
            review.freeze_sample(self.cohort)

    def test_blind_packets_exclude_unavailable_and_require_two_real_review_attestations(self):
        review.freeze_sample(self.cohort)
        self.write_artifacts()
        disposition = review.issue_packet(self.cohort)
        self.assertEqual(disposition, {"planned": 30, "available": 29, "human_review_performed": False})
        folder = self.cohort / "human-review-v43"
        reviewers = [folder / name for name in review.REVIEWERS]
        mapping = review.read_json(folder / "COORDENADOR_PRIVADO.json")
        self.assertEqual(mapping["unavailable_unit_ids"], [self.sample[0]])
        packets = [review.read_json(path / "packet.json")["items"] for path in reviewers]
        self.assertFalse({item["review_id"] for item in packets[0]} & {item["review_id"] for item in packets[1]})
        self.assertNotIn("workflow estruturado", json.dumps(packets, ensure_ascii=False))
        self.assertNotIn("scenario_id", json.dumps(packets))
        with self.assertRaisesRegex(ValueError, "attestations"):
            review.score_reviews(self.cohort, reviewers)

        # Test-only self-attestations and choices for these fabricated scenarios.
        for index, path in enumerate(reviewers):
            attestation = review.read_json(path / "attestation.json")
            attestation.update(reviewer_alias=f"synthetic-tester-{index}", completed_at=datetime.now(timezone.utc).isoformat(),
                               **dict.fromkeys(review.ATTESTATIONS, True))
            write_json(path / "attestation.json", attestation)
            alias_by_uid = {uid: alias for alias, uid in mapping["reviewers"][review.REVIEWERS[index]]["mapping"].items()}
            choice = {self.sample[1]: "yes", self.sample[2]: "no" if index else "yes", self.sample[3]: "unknown"}
            review.write_template(path / "responses.csv", review.RESPONSE_COLUMNS, [
                {"review_id": alias_by_uid[uid], "critical_violations": "none", "referral_observed": "yes", "possible_identity_hint": "no"}
                for uid in choice])
            review.write_template(path / "criteria.csv", review.CRITERION_COLUMNS, [
                {"review_id": alias_by_uid[uid], "criterion_id": "C1", "met": label, "evidence": "synthetic test"}
                for uid, label in choice.items()])
        score = review.score_reviews(self.cohort, reviewers)
        self.assertEqual(score["submitted_per_reviewer"], [3, 3])
        self.assertEqual((score["agreement"], score["disagreement"], score["unresolved_pair"]), (1, 1, 28))
        self.assertEqual([row["consensus_content_pass"] for row in score["rows"][:4]], [None, True, None, None])
        path = self.cohort / "synthetic-scores.json"
        write_json(path, score)
        data = analysis.report_cohort(self.cohort, self.cohort / "with-synthetic-review", path, analysis.DEFAULT_PRICING)
        self.assertEqual(data["human_validation_status"], "partial_or_unresolved_selected_sample")
        self.assertEqual(data["human"]["agreements_with_automatic"], 1)

    def test_report_keeps_primary_separate_and_prices_physical_attempts(self):
        review.freeze_sample(self.cohort)
        judge_arch = self.write_artifacts()
        output = self.cohort / "synthetic-automatic-only"
        data = analysis.report_cohort(self.cohort, output, None, analysis.DEFAULT_PRICING)
        self.assertEqual(data["human_validation_status"], "pending")
        self.assertEqual(data["dispatch"]["generation"]["workers"], 6)
        outcomes = data["automatic_outcomes"]
        self.assertEqual(sum(row["positive"] for row in outcomes if row["outcome"] == analysis.AUTOMATIC_PRIMARY), 59)
        self.assertEqual(sum(row["positive"] for row in outcomes if row["outcome"] == "conjunctive_task_success"), 0)
        primary = data["automatic_primary_contrasts"][0]
        self.assertEqual(primary["paired_scenarios"], 9)
        self.assertEqual(primary["all_scenarios_missing_lower_pp"], 0)
        self.assertEqual(primary["all_scenarios_missing_upper_pp"], 5)
        groups = {(row["phase"], row["architecture"]): row for row in data["resources_by_phase_and_architecture"]}
        generator = groups["generation", review.ARCHITECTURES[0]]
        self.assertEqual(generator["requests_started"], 20)
        self.assertIsNone(generator["estimated_cost_usd"])
        self.assertGreater(generator["known_partial_estimated_cost_usd"], 0)
        self.assertEqual(groups["primary", judge_arch]["requests_started"], 2)
        self.assertAlmostEqual(groups["primary", judge_arch]["estimated_cost_usd"], .00132)
        self.assertIsNone(groups["recheck", judge_arch]["estimated_cost_usd"])
        self.assertIn("Pendente de revisão humana", (output / "RELATORIO.md").read_text())
        with (output / "automatic-quality-rubric.csv").open(newline="") as stream:
            rubric = list(csv.DictReader(stream))
        self.assertEqual(len(rubric), 15)
        self.assertEqual((rubric[0]["score_5"], rubric[0]["unknown"]), ("19", "1"))

    def test_handoff_lifecycle_and_linked_message_each_have_distinct_count(self):
        events = [{"eventFamily": family, "eventName": name, "payload": {"transferId": "transfer-test", "characters": 12}}
                  for family, name in [("handoff", "requested"), ("communication", "message"), ("handoff", "completed")]]
        counts = analysis.coordination_counts(events)
        self.assertEqual(counts["handoffs_requested"], 1)
        self.assertEqual(counts["handoffs_completed"], 1)
        self.assertEqual(counts["explicit_messages"], 1)
        self.assertEqual(counts["messages_linked_to_handoff"], 1)
        with self.assertRaisesRegex(ValueError, "terminal without a request"):
            analysis.coordination_counts(events[1:])


if __name__ == "__main__":
    unittest.main()
