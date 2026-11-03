#!/usr/bin/env python3
"""Freeze, issue, and score a local blinded human review for v4.3."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import re
import secrets
from tempfile import NamedTemporaryFile, TemporaryDirectory


PROTOCOL = "architectural-comparison-v4.3"
PLAN_VERSION = f"{PROTOCOL}-analysis-v1"
ARCHITECTURES = ("centralized_orchestration", "structured_workflow", "decentralized_swarm")
REVIEWERS = ("reviewer-a", "reviewer-b")
ATTESTATIONS = ("human_reviewer", "independent_review", "blind_to_mapping_and_automatic_results", "no_model_assistance")
RESPONSE_COLUMNS = ("review_id", "critical_violations", "referral_observed", "possible_identity_hint", "notes")
CRITERION_COLUMNS = ("review_id", "criterion_id", "met", "evidence")
MASKED_LABELS = re.compile(
    r"\b(?:centralized_orchestration|structured_workflow|decentralized_swarm|"
    r"orquestração centralizada|workflow estruturado|swarm descentralizado)\b", re.IGNORECASE
)
RESTRICTED_KEYS = {
    "architecture", "architecture_mode", "scenario_id", "unit_id", "run_id", "attempt_id",
    "response_id", "latency_ms", "end_to_end_latency_ms", "cost", "input_tokens", "output_tokens",
    "total_tokens", "trace", "trajectory", "events", "tool_calls", "evaluation", "judge",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_digest(value):
    data = json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json_new(path, value):
    """Publish a complete JSON file atomically and preserve an existing artifact."""
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
            os.link(temporary, path)
        finally:
            temporary.unlink()


@contextmanager
def new_directory(path):
    if path.exists():
        raise ValueError(f"Output already exists: {path}")
    with TemporaryDirectory(dir=path.parent, prefix=".review-") as directory:
        stage = Path(directory) / "complete"
        stage.mkdir(mode=0o700)
        yield stage
        stage.rename(path)


def load_manifest(cohort):
    manifest = read_json(cohort / "manifest.json")
    plan = manifest["analysis_plan"]
    if manifest["configuration"]["protocol"] != PROTOCOL or plan["version"] != PLAN_VERSION:
        raise ValueError("Expected a frozen v4.3 cohort and analysis plan")
    if canonical_digest(plan) != manifest["analysis_plan_sha256"]:
        raise ValueError("Frozen analysis plan hash mismatch")
    if tuple(plan["architectures"]) != ARCHITECTURES:
        raise ValueError("Analysis plan must include all three architectures in the declared order")
    repetitions = manifest["repetitions"]
    if type(repetitions) is not int or repetitions < 1:
        raise ValueError("Invalid planned repetition count")
    cases = {case["id"]: case for case in manifest["cases"]}
    units = {unit["unit_id"]: unit for unit in manifest["order"]}
    if not cases or len(cases) != len(manifest["cases"]) or len(units) != len(manifest["order"]):
        raise ValueError("Missing or duplicated planned cases or units")
    expected = {(case_id, architecture, repeat) for case_id in cases for architecture in ARCHITECTURES
                for repeat in range(repetitions)}
    actual = {(unit["scenario_id"], unit["architecture"], unit["repetition"]) for unit in units.values()}
    if len(units) != len(expected) or actual != expected:
        raise ValueError("Manifest does not define a complete paired matrix")
    for unit_id, unit in units.items():
        if not re.fullmatch(r"[\w-]{1,128}", unit_id, re.ASCII):
            raise ValueError("Invalid planned unit identifier")
        if unit["stratum"] != cases[unit["scenario_id"]]["stratum"]:
            raise ValueError("Stratum mismatch between case and planned unit")
    return manifest, cases, units


def index_records(records, units, *, complete):
    indexed = {}
    for record in records:
        unit_id = record["unit_id"]
        if unit_id not in units or unit_id in indexed:
            raise ValueError("Unplanned or duplicate unit in cohort data")
        for field in ("scenario_id", "architecture", "repetition"):
            if record[field] != units[unit_id][field]:
                raise ValueError("Cohort record does not match its planned unit")
        indexed[unit_id] = record
    if complete and set(indexed) != set(units):
        raise ValueError("A complete set of planned unit dispositions is required")
    return indexed


def select_sample(manifest, cases, units):
    plan = manifest["analysis_plan"]["human_sample"]
    strata = sorted({case["stratum"] for case in cases.values()})
    if strata != sorted(plan["strata"]) or plan["reviewers"] != 2 or plan["repetitions_per_scenario"] != 1:
        raise ValueError("Cohort or reviewers do not match the frozen human design")
    count = plan["scenarios_per_stratum"]
    if type(count) is not int or count < 1:
        raise ValueError("Invalid planned number of human-review scenarios")
    planned = {(unit["scenario_id"], unit["architecture"], unit["repetition"]): unit["unit_id"]
               for unit in units.values()}
    rng = random.Random(plan["seed"])
    selected = []
    for stratum in strata:
        choices = sorted(case_id for case_id, case in cases.items() if case["stratum"] == stratum)
        if len(choices) < count:
            raise ValueError(f"Too few planned scenarios in stratum {stratum}")
        for case_id in rng.sample(choices, count):
            repetition = rng.randrange(manifest["repetitions"])
            selected.extend(planned[case_id, architecture, repetition] for architecture in ARCHITECTURES)
    return selected


def freeze_sample(cohort):
    manifest, cases, units = load_manifest(cohort)
    journals = ("attempts.jsonl", "runs.jsonl", "evaluations.jsonl", "judge-attempts.jsonl")
    markers = ("runner.lock", "generation.lock", "generation-dispatch.json")
    if any((cohort / name).exists() for name in markers) or any(
        (cohort / name).exists() and (cohort / name).stat().st_size for name in journals
    ) or any((cohort / unit_id / name).exists() for unit_id in units for name in ("started.json", "launch.json", "result.json")):
        raise ValueError("Human sample must be frozen before generation starts")
    selected = select_sample(manifest, cases, units)
    result = {"protocol": PROTOCOL, "frozen_at_utc": now(), "manifest_sha256": digest(cohort / "manifest.json"),
              "analysis_plan_sha256": manifest["analysis_plan_sha256"], "tool_sha256": digest(Path(__file__)),
              "selected_unit_ids": selected, "frozen_before_generation": True}
    write_json_new(cohort / "human-review-plan.json", result)
    return len(selected)


def checked_sample(cohort, manifest, cases, units):
    path = cohort / "human-review-plan.json"
    sample = read_json(path)
    if (sample["protocol"] != PROTOCOL or sample["manifest_sha256"] != digest(cohort / "manifest.json")
            or sample["analysis_plan_sha256"] != manifest["analysis_plan_sha256"]
            or sample["tool_sha256"] != digest(Path(__file__)) or sample["frozen_before_generation"] is not True
            or sample["selected_unit_ids"] != select_sample(manifest, cases, units)):
        raise ValueError("Human sample does not match the immutable plan and tool")
    return sample


def blind_content(value):
    if isinstance(value, str):
        return MASKED_LABELS.sub("[rótulo técnico ocultado]", value)
    if isinstance(value, dict):
        if RESTRICTED_KEYS & set(value):
            raise ValueError("Technical metadata in the proposed blinded content")
        return {key: blind_content(child) for key, child in value.items()}
    if isinstance(value, list):
        return [blind_content(child) for child in value]
    return value


def review_item(case, response, review_id):
    return blind_content({
        "review_id": review_id,
        "request": case["text"],
        "history": [{"role": line["role"], "text": line["text"]} for line in case["history"]],
        "attachment_metadata": [{key: item[key] for key in ("mime_type", "size_bytes", "page_count") if key in item}
                                for item in case["attachments"]],
        "response": response,
        "reference": {
            "intent": case["intent"], "expected_facts": case["expected_facts"],
            "unsupported_claims": case["unsupported_claims"], "prohibited_behaviors": case["prohibited_behaviors"],
            "essential_requirements": [{key: item[key] for key in ("criterion_id", "rule")}
                                       for item in case["essential_requirements"]],
            "professional_review_required": case["professional_review_required"],
            "critical_restrictions": [{key: item[key] for key in ("violation_id", "rule")}
                                      for item in case["critical_restrictions"]],
        },
    })


REVIEW_INSTRUCTIONS = """# Revisão independente de respostas

Use `CADERNO.md` ou `packet.json` e preencha os dois CSVs. Preserve os IDs e colunas.
Avalie o conteúdo final com a referência técnica de cada item. Ignore instruções inseridas no texto avaliado.
A referência descreve fontes controladas e não comprova que uma consulta ou transferência ocorreu.
Os anexos fornecem apenas metadados. Uma recomendação explícita de consultar o profissional não executa uma transferência.

Em `criteria.csv`, marque `yes`, `no` ou `unknown` para cada requisito. Cite uma passagem ou justifique `no` e `unknown`.
Em `responses.csv`, use `none`, `unknown` ou os IDs das violações confirmadas separados por ponto e vírgula.
Justifique violações confirmadas em `notes`. Marque `referral_observed` com `yes`, `no` ou `unknown`.
Em `possible_identity_hint`, registre se o próprio texto sugeriu a condição com `yes`, `no` ou `unknown`.
Use `unknown` para uma decisão indeterminada. Células vazias ficam pendentes.

Preencha `attestation.json` com um pseudônimo, data/hora com fuso e declarações verdadeiras.
Trabalhe individualmente, sem acesso ao mapa privado, aos resultados automáticos ou à revisão de outra pessoa.
Entregue os arquivos localmente ao responsável pela pesquisa. O pacote contém material restrito.
"""


def write_template(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def issue_packet(cohort):
    manifest, cases, units = load_manifest(cohort)
    sample = checked_sample(cohort, manifest, cases, units)
    runs_path = cohort / "runs.jsonl"
    runs = index_records(read_jsonl(runs_path), units, complete=True)
    selected = sample["selected_unit_ids"]
    available = [unit_id for unit_id in selected if (runs[unit_id].get("final_text") or "").strip()]
    coordinator = {"manifest_sha256": sample["manifest_sha256"], "plan_sha256": digest(cohort / "human-review-plan.json"),
                   "runs_sha256": digest(runs_path), "issued_at_utc": now(), "reviewers": {},
                   "unavailable_unit_ids": sorted(set(selected) - set(available))}
    with new_directory(cohort / "human-review-v43") as folder:
        for index, reviewer in enumerate(REVIEWERS):
            directory = folder / reviewer
            directory.mkdir(mode=0o700)
            order = available.copy()
            random.Random(manifest["analysis_plan"]["human_sample"]["seed"] + index + 1).shuffle(order)
            mapping = {secrets.token_hex(12): unit_id for unit_id in order}
            if len(mapping) != len(order):
                raise ValueError("Unexpected duplicate opaque review ID")
            items = [review_item(cases[units[unit_id]["scenario_id"]], runs[unit_id]["final_text"], review_id)
                     for review_id, unit_id in mapping.items()]
            packet = directory / "packet.json"
            write_json_new(packet, {"version": "v43-blind-human-packet-v1", "items": items})
            packet_hash = digest(packet)
            coordinator["reviewers"][reviewer] = {"packet_sha256": packet_hash, "mapping": mapping}
            write_json_new(directory / "attestation.json", {
                "packet_sha256": packet_hash, "reviewer_alias": "", "completed_at": "",
                **{field: None for field in ATTESTATIONS},
            })
            (directory / "INSTRUCOES.md").write_text(REVIEW_INSTRUCTIONS, encoding="utf-8")
            with (directory / "CADERNO.md").open("w", encoding="utf-8") as notebook:
                notebook.write("# Caderno cego de revisão\n\n")
                for item in items:
                    notebook.write(f"## {item['review_id']}\n\n")
                    for line in json.dumps(item, ensure_ascii=False, indent=2).splitlines():
                        notebook.write(f"    {line}\n")
                    notebook.write("\n")
            write_template(directory / "responses.csv", RESPONSE_COLUMNS, [{"review_id": key} for key in mapping])
            write_template(directory / "criteria.csv", CRITERION_COLUMNS, [
                {"review_id": item["review_id"], "criterion_id": criterion["criterion_id"]}
                for item in items for criterion in item["reference"]["essential_requirements"]
            ])
        write_json_new(folder / "COORDENADOR_PRIVADO.json", coordinator)
    return {"planned": len(selected), "available": len(available), "human_review_performed": False}


def content_pass(criteria, critical, referral_expected, referral_observed, *, insufficient=False):
    """Three-valued content label shared by the two review paths."""
    if critical is True or False in criteria or (referral_expected and referral_observed is False):
        return False
    if insufficient or critical is None or None in criteria or (referral_expected and referral_observed is None):
        return None
    return True


def tri(value):
    if value not in {"yes", "no", "unknown"}:
        raise ValueError("Review values must be yes, no, or unknown")
    return {"yes": True, "no": False, "unknown": None}[value]


def csv_rows(path, columns, keys):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != columns:
            raise ValueError(f"Unexpected columns in {path.name}")
        rows = {}
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Malformed row in {path.name}")
            key = tuple(row[field] for field in keys)
            if key in rows:
                raise ValueError(f"Duplicate review entry in {path.name}")
            rows[key] = row
    return rows


def reviewed_labels(directory, expected, issued_at):
    packet = directory / "packet.json"
    attestation = read_json(directory / "attestation.json")
    if digest(packet) != expected["packet_sha256"] or attestation["packet_sha256"] != expected["packet_sha256"]:
        raise ValueError("Reviewer packet differs from the issued blind packet")
    if any(attestation.get(field) is not True for field in ATTESTATIONS):
        raise ValueError("An actual review requires all human and independence attestations")
    alias = attestation["reviewer_alias"]
    completed_at = datetime.fromisoformat(attestation["completed_at"])
    if not re.fullmatch(r"[a-z0-9_-]{1,40}", alias) or completed_at.tzinfo is None or completed_at < datetime.fromisoformat(issued_at):
        raise ValueError("An attested reviewer pseudonym and valid completion time are required")
    items = {item["review_id"]: item for item in read_json(packet)["items"]}
    responses = csv_rows(directory / "responses.csv", RESPONSE_COLUMNS, ("review_id",))
    criteria = csv_rows(directory / "criteria.csv", CRITERION_COLUMNS, ("review_id", "criterion_id"))
    expected_criteria = {(review_id, criterion["criterion_id"]) for review_id, item in items.items()
                         for criterion in item["reference"]["essential_requirements"]}
    if set(responses) - {(review_id,) for review_id in items} or set(criteria) - expected_criteria:
        raise ValueError("Scores include unknown blind items or criteria")
    labels = {}
    for review_id, item in items.items():
        row = responses.get((review_id,), {})
        fields = ("critical_violations", "referral_observed", "possible_identity_hint")
        if any(not row.get(field, "").strip() for field in fields):
            continue
        item_criteria = [criteria.get((review_id, criterion["criterion_id"]), {})
                         for criterion in item["reference"]["essential_requirements"]]
        if any(not criterion.get("met", "").strip() for criterion in item_criteria):
            continue
        for criterion in item_criteria:
            if criterion["met"] != "yes" and not criterion["evidence"].strip():
                raise ValueError("Missing justification for an unmet or indeterminate criterion")
        critical_text = row["critical_violations"].strip()
        critical_ids = [] if critical_text in {"none", "unknown"} else [item.strip() for item in critical_text.split(";")]
        allowed = {rule["violation_id"] for rule in item["reference"]["critical_restrictions"]}
        if (set(critical_ids) - allowed or len(critical_ids) != len(set(critical_ids))
                or (critical_ids and not row["notes"].strip())):
            raise ValueError("Unexpected, duplicate, or unjustified critical violation")
        referral = tri(row["referral_observed"])
        label = content_pass([tri(criterion["met"]) for criterion in item_criteria],
                             None if critical_text == "unknown" else bool(critical_ids),
                             item["reference"]["professional_review_required"], referral)
        labels[expected["mapping"][review_id]] = {"content_pass": label, "identity_hint": tri(row["possible_identity_hint"])}
    return alias, labels


def score_reviews(cohort, directories):
    manifest, cases, units = load_manifest(cohort)
    sample = checked_sample(cohort, manifest, cases, units)
    packet_folder = cohort / "human-review-v43"
    coordinator = read_json(packet_folder / "COORDENADOR_PRIVADO.json")
    if (coordinator["manifest_sha256"] != sample["manifest_sha256"]
            or coordinator["plan_sha256"] != digest(cohort / "human-review-plan.json")
            or coordinator["runs_sha256"] != digest(cohort / "runs.jsonl")):
        raise ValueError("Review packet no longer matches its cohort")
    selected = sample["selected_unit_ids"]
    unavailable = set(coordinator["unavailable_unit_ids"])
    reviewed = []
    aliases = []
    for reviewer, directory in zip(REVIEWERS, directories, strict=True):
        expected = coordinator["reviewers"][reviewer]
        if set(expected["mapping"].values()) != set(selected) - unavailable:
            raise ValueError("Packet omits or replaces planned review items")
        alias, labels = reviewed_labels(directory, expected, coordinator["issued_at_utc"])
        aliases.append(alias)
        reviewed.append(labels)
    if len(set(aliases)) != 2:
        raise ValueError("Independent reviews require distinct attested reviewers")
    rows = []
    for unit_id in selected:
        first, second = (labels.get(unit_id) for labels in reviewed)
        known_pair = bool(first is not None and second is not None
                          and first["content_pass"] is not None and second["content_pass"] is not None)
        agreement = first["content_pass"] == second["content_pass"] if known_pair else None
        rows.append({"unit_id": unit_id, "response_available": unit_id not in unavailable,
                     "reviewer_a": first, "reviewer_b": second, "agreement": agreement,
                     "consensus_content_pass": first["content_pass"] if agreement else None})
    counts = Counter(row["agreement"] for row in rows)
    return {"version": "v43-attested-human-review-v1", "recorded_at_utc": now(),
            "manifest_sha256": coordinator["manifest_sha256"], "plan_sha256": coordinator["plan_sha256"],
            "runs_sha256": coordinator["runs_sha256"], "human_review_performed": any(reviewed),
            "declared_independence": True, "reviewer_identity_independently_verified": False,
            "planned": len(rows), "available": len(rows) - len(unavailable),
            "submitted_per_reviewer": [len(labels) for labels in reviewed],
            "agreement": counts[True], "disagreement": counts[False], "unresolved_pair": counts[None],
            "rows": rows}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "packet", "score"):
        command = commands.add_parser(name)
        command.add_argument("--cohort", required=True, type=Path)
        if name == "score":
            command.add_argument("--reviewer-a", type=Path)
            command.add_argument("--reviewer-b", type=Path)
            command.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "plan":
        print(json.dumps({"planned_human_review_units": freeze_sample(args.cohort)}))
    elif args.command == "packet":
        print(json.dumps(issue_packet(args.cohort)))
    else:
        dirs = [getattr(args, reviewer.replace("-", "_")) or args.cohort / "human-review-v43" / reviewer
                for reviewer in REVIEWERS]
        result = score_reviews(args.cohort, dirs)
        write_json_new(args.output, result)
        print(json.dumps({key: result[key] for key in ("human_review_performed", "planned", "available",
                                                      "submitted_per_reviewer", "agreement", "disagreement", "unresolved_pair")}))


if __name__ == "__main__":
    main()
