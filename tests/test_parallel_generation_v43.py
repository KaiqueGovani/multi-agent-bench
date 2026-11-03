from collections import Counter
import json
from pathlib import Path
import sys
from threading import Barrier, Lock
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import run_research_pilot as collector


def test_balanced_waves_stop_on_capacity_and_resume_only_unstarted(tmp_path, monkeypatch):
    cases = [{"id": f"case-{i}", "stratum": "faq", "difficulty": "low"} for i in range(4)]
    experiment_id = str(uuid4())
    order = collector.build_order(cases, 1, 111, experiment_id)
    manifest = {
        "code_hashes": {},
        "cases": cases,
        "order": order,
        "generation_dispatch": {"workers": 6},
    }
    monkeypatch.setattr(collector, "code_hashes", dict)
    monkeypatch.setattr(collector, "validate_environment", lambda _: None)
    barrier = Barrier(6, timeout=5)
    attempts = Counter()
    waves = {}
    mutex = Lock()

    def fake_unit(folder, manifest, case, unit, stop, wave, wave_size):
        target = folder / unit["unit_id"]
        target.mkdir(exist_ok=True)
        result_path = target / "result.json"
        if result_path.exists():
            return json.loads(result_path.read_text())
        with mutex:
            attempts[unit["unit_id"]] += 1
            waves.setdefault(wave, []).append(unit)
        barrier.wait()
        throttled = unit["global_position"] == 0
        record = {
            **unit,
            "attempt_id": str(uuid4()),
            "success": not throttled,
            "provider_error_types": ["ThrottlingException"] if throttled else [],
        }
        collector.dump(result_path, record)
        return record

    monkeypatch.setattr(collector, "collect_parallel_unit", fake_unit)
    collector.dump(tmp_path / "manifest.json", manifest)
    assert collector.collect_parallel(tmp_path, manifest, continue_after_failure=True) == 1
    assert len(attempts) == 6
    assert set(waves) == {1}

    assert collector.collect_parallel(tmp_path, manifest, continue_after_failure=True) == 1
    assert len(attempts) == 12
    assert all(count == 1 for count in attempts.values())
    assert set(waves) == {1, 2}
    for wave in waves.values():
        assert Counter(unit["architecture"] for unit in wave) == dict.fromkeys(collector.ARCHITECTURES, 2)
        assert set(Counter(unit["block_id"] for unit in wave).values()) == {3}
    results = [json.loads(line) for line in (tmp_path / "runs.jsonl").read_text().splitlines()]
    assert [row["unit_id"] for row in results] == [row["unit_id"] for row in order]
    assert sum(not row["success"] for row in results) == 1
    assert len((tmp_path / "attempts.jsonl").read_text().splitlines()) == len(order)
