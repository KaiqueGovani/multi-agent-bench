"""Controlled provider smoke tests only. Temporary synthetic files are discarded."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location("private_parallel_judge", BASE / "parallel_judge.py")
dispatcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dispatcher)
j = dispatcher.judge
c = dispatcher.collector


class ParallelJudgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="controlled-judge-only-")
        self.folder = Path(self.temp.name) / "cohort"
        self.folder.mkdir()
        self.calibration = Path(self.temp.name) / "calibration"
        self.calibration.mkdir()
        cfg = j.config()
        c.dump(self.calibration / "calibration-gate.json", {"passed": True, "controlled_test_only": True})
        c.dump(self.calibration / "judge-config.json", cfg)
        self.case = json.loads((dispatcher.ROOT / "experiments/pilots-v5/pilot-b.json").read_text())["cases"][0]
        self.items = [{"evaluation_id": f"{i:024x}", "input": self.case, "response": "Synthetic controlled response"} for i in range(1, 9)]
        c.dump(self.folder / "manifest.json", {"order": [{"unit_id": str(i)} for i in range(8)],
            "code_hashes": c.code_hashes(), "evaluation_plan": {"configuration_sha256": dispatcher.config_hash(cfg)}})
        c.dump(self.folder / "blind-responses.json", self.items)
        for i in range(8):
            c.append(self.folder / "runs.jsonl", {"unit_id": str(i)})
        self.calls, self.active, self.maximum = [], 0, 0
        self.guard = threading.Lock()
        self.payloads = {}

    def tearDown(self):
        self.temp.cleanup()

    def fake_converse(self, cfg, prompt, system=None):
        if prompt.startswith("{"):
            payload = json.loads(prompt)
            rid = payload["response_id"]
            self.payloads[rid] = payload
            repair = False
        else:
            rid = re.search(r"Identificador ([a-f0-9]{24})", prompt).group(1)
            payload, repair = self.payloads[rid], True
        def keys(value):
            if isinstance(value, dict):
                return set(value) | set().union(*(keys(v) for v in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(v) for v in value))
            return set()
        self.assertFalse(keys(payload) & {"architecture", "architecture_mode", "latency_ms", "cost", "total_tokens"})
        self.assertEqual(cfg["prompt_sha256"], "ac77d9d9800bd6830102e5760a4d848330c3bcfcfa6d65b7d5723713f9478e36")
        with self.guard:
            self.calls.append((rid, repair))
            self.active += 1
            self.maximum = max(self.maximum, self.active)
        time.sleep(.02)
        with self.guard:
            self.active -= 1
        if rid.endswith("4"):
            raise RuntimeError("controlled provider failure; never retried")
        if rid.endswith("3") and not repair:
            return "{", {"inputTokens": 11, "outputTokens": 1, "totalTokens": 12}, "end_turn"
        value = {"evaluation_id": rid, "response_id": rid,
            "criteria": [{"criterion_id": criterion["criterion_id"], "met": True, "evidence_refs": ["R1"], "reason": "controlled fixture"} for criterion in self.case["essential_requirements"]],
            "quality": {key: 5 for key in j.EvaluationV5.model_fields["quality"].annotation.model_fields},
            "quality_reasons": {key: "controlled fixture" for key in j.EvaluationV5.model_fields["quality"].annotation.model_fields},
            "referral_expected": False, "referral_recommendation_observed": False, "referral_evidence": None,
            "transfer_executed": False, "transfer_claimed_in_response": False, "transfer_evidence": "T1",
            "critical_violations": [], "evidence_insufficient": False, "insufficiency_reason": None,
            "review_reason_codes": []}
        raw = json.dumps(value)
        if rid.endswith("2"):
            raw = "```json\n" + raw + "\n```"
        return raw, {"inputTokens": 11, "outputTokens": 5, "totalTokens": 16}, "end_turn"

    def prepared(self):
        return dispatcher.prepare(self.folder, self.calibration, 4, "primary", expected_units=8)

    def execute_all(self, dispatch):
        cfg = j.config()
        def worker(index):
            part = dispatcher.read(dispatcher.phase_path(self.folder, "primary") / f"worker-{index:02d}" / "blind-partition.json")
            for item in part:
                dispatcher.execute_one(self.folder, dispatch, item, index, cfg)
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(worker, range(1, 5)))

    def test_parallel_owners_original_judge_semantics_and_single_counted_merge(self):
        dispatch = self.prepared()
        self.assertEqual(len({row["response_id"] for row in dispatch["assignments"]}), 8)
        self.assertTrue(all(sum(row["worker"] == i for row in dispatch["assignments"]) == 2 for i in range(1, 5)))
        with patch.object(j, "converse", self.fake_converse):
            self.execute_all(dispatch)
            merge = dispatcher.CentralMerge(self.folder, dispatch)
            self.assertEqual(merge.merge_ready(), 8)
            self.assertEqual(len(dispatcher.lines(self.folder / "evaluations.jsonl")), 7)
            self.assertEqual(len(dispatcher.lines(self.folder / "evaluation-failures.jsonl")), 1)
            journal = dispatcher.lines(self.folder / "judge-attempts.jsonl")
            starts = [event for event in journal if event["event"] == "started"]
            self.assertEqual(len(starts), 9)  # original eight + one allowed format repair
            self.assertEqual(len({event["attempt_id"] for event in starts}), 9)
            self.assertEqual(sum(event["format_repair"] for event in starts), 1)
            self.assertEqual(sum(bool(event.get("local_format_repair")) for event in journal if event["event"] == "completed"), 1)
            self.assertGreaterEqual(self.maximum, 2)
            original = (self.folder / "judge-attempts.jsonl").read_bytes()
            calls = len(self.calls)
            self.execute_all(dispatch)
            self.assertEqual(merge.merge_ready(), 8)
            self.assertEqual(len(self.calls), calls)
            self.assertEqual((self.folder / "judge-attempts.jsonl").read_bytes(), original)
            self.assertEqual(sum(rid.endswith("4") for rid, _ in self.calls), 1)

    def test_started_dead_owner_is_preserved_without_new_request(self):
        dispatch = self.prepared()
        assignment = dispatch["assignments"][0]
        rid = assignment["response_id"]
        unit = dispatcher.phase_path(self.folder, "primary") / "responses" / rid
        unit.mkdir(parents=True)
        c.dump(unit / "claim.json", {"worker": assignment["worker"], "pid": 0})
        c.append(unit / "judge-attempts.jsonl", {"event": "started", "attempt_id": "interrupted-first", "response_id": rid, "phase": "primary", "format_repair": 0})
        with patch.object(j, "converse", side_effect=AssertionError("must not infer")):
            result = dispatcher.execute_one(self.folder, dispatch, self.items[0], assignment["worker"], j.config())
        self.assertEqual(result["kind"], "failure")
        self.assertEqual(result["row"]["attempt_id"], "interrupted-first")
        self.assertEqual(len(dispatcher.lines(unit / "judge-attempts.jsonl")), 1)

    def test_four_real_subprocesses_resume_only_completed_controlled_owners(self):
        dispatch = self.prepared()
        with patch.object(j, "converse", self.fake_converse):
            self.execute_all(dispatch)
        # All eight result markers exist before launching real subprocesses.
        # Children may only read those completed controlled records: no provider
        # credentials or mock fallback are exposed through the production CLI.
        units = dispatcher.phase_path(self.folder, "primary") / "responses"
        self.assertEqual(len(list(units.glob("*/result.json"))), 8)
        before = {path.parent.name: path.read_bytes() for path in units.glob("*/judge-attempts.jsonl")}
        with patch.object(dispatcher, "prepare", return_value=dispatch):
            self.assertEqual(dispatcher.run_phase(self.folder, self.calibration, 4, "primary"), 0)
        after = {path.parent.name: path.read_bytes() for path in units.glob("*/judge-attempts.jsonl")}
        self.assertEqual(before, after)
        summary = dispatcher.read(dispatcher.phase_path(self.folder, "primary") / "summary.json")
        self.assertEqual(summary["worker_exit_codes"], [0, 0, 0, 0])

    def test_wrong_worker_cannot_claim_or_infer(self):
        dispatch = self.prepared()
        with patch.object(j, "converse", side_effect=AssertionError("must not infer")):
            with self.assertRaisesRegex(ValueError, "does not own"):
                dispatcher.execute_one(self.folder, dispatch, self.items[0], 2, j.config())
        self.assertFalse((dispatcher.phase_path(self.folder, "primary") / "responses").exists())

    def test_existing_central_start_is_never_redispatched(self):
        c.append(self.folder / "judge-attempts.jsonl", {"event": "started", "phase": "primary", "response_id": self.items[0]["evaluation_id"], "attempt_id": "prior"})
        with self.assertRaisesRegex(ValueError, "lack dispositions"):
            self.prepared()

    def test_original_prefix_retained_and_already_failed_id_has_no_owner(self):
        rid = self.items[0]["evaluation_id"]
        c.append(self.folder / "evaluation-failures.jsonl", {"response_id": rid, "attempt_id": "prior", "phase": "primary"})
        prefix = (self.folder / "evaluation-failures.jsonl").read_bytes()
        dispatch = self.prepared()
        self.assertEqual(dispatch["new_owned_responses"], 7)
        self.assertNotIn(rid, {row["response_id"] for row in dispatch["assignments"]})
        self.assertEqual((dispatcher.phase_path(self.folder, "primary") / "original-prefix/evaluation-failures.jsonl").read_bytes(), prefix)
        self.assertEqual((self.folder / "evaluation-failures.jsonl").read_bytes(), prefix)


if __name__ == "__main__":
    unittest.main(verbosity=2)
