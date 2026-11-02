"""Focused analysis integrity tests; run with research-data/local/figures-env/bin/python.

Uses unittest so the frozen figure environment needs no new dependencies.
"""
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np

_path = Path(__file__).resolve().parents[1] / "scripts" / "summarize_corrected_comparison.py"
_spec = importlib.util.spec_from_file_location("corrected_summary", _path)
summary_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(summary_module)


def row(**changes):
    base = {
        "architecture": summary_module.ARCHES[0], "scenario_id": "synthetic-case",
        "stratum": "faq", "difficulty": "low", "success": True,
        "architectural_compliance": True, "task_success": True,
        "procedure_applicable": True, "procedure_compliance": True,
        "evaluation": {"criteria": [{"met": True}], "critical_violations": [], "evidence_insufficient": False},
        "objective_checks": {"critical_violations": [], "required_evidence": [{"met": True}]},
        "estimated_generation_cost_usd": 0.1,
    }
    base.update(changes)
    return base


class PairedScenarioStatisticsTests(unittest.TestCase):
    def test_exact_test_and_percentile_interval_use_scenario_differences(self):
        actual = summary_module.paired_success([0.2, 0.2], bootstraps=1000)
        self.assertAlmostEqual(actual["difference_pp_b_minus_a"], 20)
        self.assertAlmostEqual(actual["bootstrap_95_low_pp"], 20)
        self.assertAlmostEqual(actual["bootstrap_95_high_pp"], 20)
        self.assertEqual(actual["p_unadjusted"], 0.5)
        self.assertEqual(actual["paired_scenarios"], 2)

    def test_zero_effect_and_balanced_effect_have_unit_p(self):
        for differences in ([0, 0, 0], [0.2, -0.2, 0]):
            with self.subTest(differences=differences):
                actual = summary_module.paired_success(differences, bootstraps=1000)
                self.assertEqual(actual["p_unadjusted"], 1)
                self.assertAlmostEqual(actual["difference_pp_b_minus_a"], 0)

    def test_monte_carlo_seed_and_plus_one_are_reproducible(self):
        a = summary_module.paired_success([0.2] * 17, bootstraps=200, permutations=999)
        b = summary_module.paired_success([0.2] * 17, bootstraps=200, permutations=999)
        self.assertEqual(a, b)
        self.assertGreaterEqual(a["p_unadjusted"], 1 / 1000)
        self.assertIn("plus-one", a["method"])

    def test_holm_corrects_all_three_comparisons_monotonically(self):
        np.testing.assert_allclose(summary_module.holm([0.04, 0.01, 0.03]), [0.06, 0.03, 0.06])


class PhysicalRequestLedgerTests(unittest.TestCase):
    rates = {"input": 1, "output": 5}
    usage = {"inputTokens": 100, "outputTokens": 20, "totalTokens": 120}

    def test_each_physical_request_is_priced_once_even_if_parent_has_children(self):
        ledger = summary_module.ledger_summary(["parent", "child"], [("parent", "completed", self.usage), ("child", "completed", self.usage)], self.rates)
        self.assertTrue(ledger["usage_complete"])
        self.assertEqual(ledger["known_totalTokens"], 240)
        self.assertAlmostEqual(ledger["estimated_cost_usd"], 0.0004)

    def test_unknown_usage_remains_unknown_and_known_failed_consumption_is_retained(self):
        ledger = summary_module.ledger_summary(["known-failure", "unknown"], [("known-failure", "failed", self.usage), ("unknown", "failed", None)], self.rates)
        self.assertFalse(ledger["usage_complete"])
        self.assertIsNone(ledger["estimated_cost_usd"])
        self.assertEqual(ledger["requests_failed"], 2)
        self.assertAlmostEqual(ledger["known_partial_estimated_cost_usd"], 0.0002)

    def test_duplicate_or_orphan_provider_records_are_rejected(self):
        invalid = [
            (["a", "a"], [("a", "completed", self.usage)]),
            (["a"], [("a", "completed", self.usage), ("a", "failed", None)]),
            (["a"], [("a", "completed", self.usage), ("orphan", "failed", None)]),
        ]
        for starts, terminals in invalid:
            with self.subTest(starts=starts, terminals=terminals), self.assertRaises(ValueError):
                summary_module.ledger_summary(starts, terminals, self.rates)

    def test_inconsistent_physical_token_total_is_rejected(self):
        with self.assertRaises(ValueError):
            summary_module.ledger_summary(["a"], [("a", "completed", {**self.usage, "totalTokens": 999})], self.rates)

    def test_cache_is_not_silently_priced_at_plain_input_rates(self):
        ledger = summary_module.ledger_summary(["a"], [("a", "completed", {**self.usage, "cacheReadInputTokens": 20})], self.rates)
        self.assertTrue(ledger["cache_usage_observed"])
        self.assertIsNone(ledger["estimated_cost_usd"])
        self.assertIsNone(ledger["known_partial_estimated_cost_usd"])

    def test_model_file_ignores_nested_agent_diagnostic_usage(self):
        import json
        events = [
            {"eventFamily": "model", "eventName": "started", "payload": {"callId": "physical"}},
            {"eventFamily": "model", "eventName": "completed", "payload": {"callId": "physical", "usage": self.usage}},
            {"eventFamily": "agent", "eventName": "completed", "payload": {"totalTokens": 1000000}},
        ]
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
            ledger = summary_module.generation_resources(Path(folder), self.rates)
        self.assertEqual(ledger["known_totalTokens"], 120)


class OutcomeClassificationTests(unittest.TestCase):
    def test_failure_precedence_and_exclusive_partition_preserve_unknowns(self):
        content = {"criteria": [{"met": False}], "critical_violations": []}
        procedure = {"critical_violations": [], "required_evidence": [{"met": False}]}
        records = [
            row(),
            row(success=False, architectural_compliance=False, task_success=False),
            row(architectural_compliance=False, task_success=False),
            row(evaluation=None, task_success=None),
            row(evaluation=content, objective_checks=procedure, task_success=False),
            row(evaluation=content, task_success=False),
            row(objective_checks=procedure, task_success=False),
            row(task_success=None),
        ]
        expected = ["success", "technical_failure_or_interruption", "architectural_contract_violation", "invalid_or_missing_judgment", "content_and_mandatory_evidence", "content_only", "mandatory_evidence_only", "unknown_or_other"]
        self.assertEqual([summary_module.failure_class(r) for r in records], expected)
        self.assertEqual(sum(summary_module.failure_class(r) != "success" for r in records), sum(r["task_success"] is not True for r in records))

    def test_content_status_does_not_inherit_architecture_or_procedure_failure(self):
        self.assertTrue(summary_module.content_status(row(architectural_compliance=False, task_success=False)))
        uncertain = row(evaluation={"criteria": [{"met": None}], "critical_violations": []})
        self.assertIsNone(summary_module.content_status(uncertain))

    def test_internal_contradiction_has_explicit_validity_denominators(self):
        contradictory = row(task_success=None, reason="evaluator internal contradiction; technical review required")
        actual = summary_module.summary(summary_module.ARCHES[0], [contradictory])
        self.assertEqual(actual["judge_schema_valid"], 1)
        self.assertEqual(actual["judge_internally_inconsistent"], 1)
        self.assertEqual(actual["judge_valid_assessment"], 0)
        self.assertEqual(actual["judge_invalid_or_missing"], 1)
        self.assertEqual(actual["task_unknown"], 1)
        self.assertIsNone(summary_module.content_status(contradictory))

    def test_consistency_keeps_five_repetitions_grouped(self):
        records = [row(repetition=i, task_success=i < 4) for i in range(5)]
        records += [row(scenario_id="unknown-case", repetition=i, task_success=None if i == 4 else True) for i in range(5)]
        actual = summary_module.summary(summary_module.ARCHES[0], records)
        self.assertEqual(actual["planned"], 10)
        self.assertEqual(actual["complete_scenarios"], 1)
        self.assertEqual(actual["task_successes"], 8)
        self.assertEqual(actual["task_unknown"], 1)
        self.assertEqual(actual["pass_1_complete"], 0.8)
        self.assertEqual(actual["pass_5_complete"], 0)


if __name__ == "__main__":
    unittest.main()
