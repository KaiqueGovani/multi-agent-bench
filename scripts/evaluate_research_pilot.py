#!/usr/bin/env python3
"""Evaluate successful pilot responses or import independent pharmacist scores."""
from __future__ import annotations
import argparse
import csv
from dataclasses import replace
import json
from pathlib import Path
import sys
from datetime import UTC, datetime

from run_research_pilot import ROOT, dump, append
from app.core.config import get_settings
from app.architectures.comparison import ControlledAgent, _extract_strands_usage
from app.experiments.judge import (DIMENSIONS, JUDGE_PROMPT, RUBRIC_VERSION, evaluate,
                                  agreement, validate_evaluation)
from strands import Agent
from strands.models.bedrock import BedrockModel
from botocore.config import Config


def import_human(path, valid_ids):
    rows = []
    seen = set()
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            key = row["evaluation_id"], row["reviewer_id"]
            if key[0] not in valid_ids or key[1] not in {"pharmacist_1", "pharmacist_2"} or key in seen:
                raise ValueError("Unknown/duplicate evaluation or reviewer ID")
            seen.add(key)
            scores = {d: None if row[d] == "NA" else int(row[d]) for d in DIMENSIONS}
            if row["critical_error"] not in {"true", "false"}:
                raise ValueError("critical_error must be true or false")
            evaluation = validate_evaluation({"scores": scores,
                "justifications": {d: row["justification"] for d in DIMENSIONS},
                "referral_adequacy": row["referral_adequacy"], "critical_error": row["critical_error"] == "true",
                "critical_error_reason": row["justification"], "reference_concerns": ""})
            rows.append({"evaluation_id": key[0], "reviewer_id": key[1], "rubric_version": RUBRIC_VERSION,
                         "recorded_at": datetime.now(UTC).isoformat(), **evaluation})
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    p.add_argument("--judge", action="store_true")
    p.add_argument("--model", help="Specify judge model; default is runtime model, with self-preference risk recorded")
    p.add_argument("--import-human", type=Path)
    args = p.parse_args()
    folder = args.folder.resolve()
    blind = json.loads((folder / "blind-responses.json").read_text())
    evaluations = folder / "evaluations.jsonl"
    rows = [json.loads(line) for line in evaluations.read_text().splitlines()] if evaluations.exists() else []
    keys = {(r["evaluation_id"], r["reviewer_id"]) for r in rows}
    if args.import_human:
        imported = import_human(args.import_human, {b["evaluation_id"] for b in blind})
        if any((r["evaluation_id"],r["reviewer_id"]) in keys for r in imported):
            raise ValueError("Evaluation already exists; prior scores will not be overwritten")
        for row in imported:
            append(evaluations, row); rows.append(row)
    if args.judge:
        if not blind:
            raise ValueError("No successful responses to evaluate")
        s = get_settings(); model_id = args.model or s.bedrock_model_id
        config = {"model_id": model_id, "region": s.aws_region, "temperature": 0.0,
                  "max_tokens": 1536, "rubric_version": RUBRIC_VERSION, "prompt": JUDGE_PROMPT,
                  "human_validation": "pending", "same_model_as_runtime": model_id == json.loads((folder / "manifest.json").read_text())["configuration"]["model_id"]}
        config_path = folder / "judge-config.json"
        if config_path.exists() and json.loads(config_path.read_text()) != config:
            raise ValueError("Judge configuration changed; create a separate evaluation experiment")
        dump(config_path, config)
        # Fresh agent per response avoids evaluation-context leakage.
        for item in blind:
            if (item["evaluation_id"], "llm_judge") in keys:
                continue
            agent = Agent(model=BedrockModel(model_id=model_id, region_name=s.aws_region, temperature=0.0,
                max_tokens=1536, stop_sequences=[], streaming=False,
                boto_client_config=Config(connect_timeout=10, read_timeout=90, retries={"total_max_attempts":1})),
                system_prompt=JUDGE_PROMPT, tools=[], callback_handler=None, retry_strategy=None)
            try:
                value, result = evaluate(agent, item)
                usage = _extract_strands_usage(result)
                row = {"evaluation_id":item["evaluation_id"], "reviewer_id":"llm_judge", "recorded_at":datetime.now(UTC).isoformat(),
                       "rubric_version":RUBRIC_VERSION, "input_tokens":usage[0], "output_tokens":usage[1],
                       "total_tokens":usage[2], **value}
                append(evaluations,row); rows.append(row)
                print(f'Evaluated {len(rows)} records',flush=True)
            except Exception as exc:
                append(folder / "judge-errors.jsonl", {"evaluation_id":item["evaluation_id"], "error_type":type(exc).__name__,
                                                       "recorded_at":datetime.now(UTC).isoformat()})
                print(f'Judge stopped: {type(exc).__name__}; no score assigned',flush=True)
                return 1
    dump(folder / "agreement.json", {"pharmacist_1_vs_2": agreement(rows,"pharmacist_1","pharmacist_2"),
                                     "judge_vs_pharmacist_1": agreement(rows,"llm_judge","pharmacist_1"),
                                     "judge_vs_pharmacist_2": agreement(rows,"llm_judge","pharmacist_2")})
    print(f'Evaluations stored: {len(rows)}; human and judge scores remain separate')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
