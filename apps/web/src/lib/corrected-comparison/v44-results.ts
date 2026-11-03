import path from "node:path";

import {
  architecture, assertNoPrivateFields, COMPARISON_ARCHITECTURES, count, inventory, number,
  parseComparisonCsv, summary, validateUnits, verifiedFile,
  type ComparisonArchitecture, type ComparisonSummary, type ResourcePhase,
} from "./results";

const RESULTS_DIRECTORY = path.resolve(process.cwd(), "../../research-data/results/architectural-comparison-v44");
const PROTOCOL = "architectural-comparison-v4.4";
const phases = ["generation", "primary", "recheck"] as const;
const additionalPrivateFields = new Set([
  "attempt_id", "candidate_text", "candidateText", "conversation_id", "raw_output", "response_id", "review_id", "run_id",
]);

export const V44_FIGURES = [
  ["01_sucesso", "Sucesso observado por arquitetura"],
  ["02_latencia_custo_sucesso", "Latência do coletor, custo e sucesso"],
  ["03_categorias", "Sucesso por categoria"],
  ["04_consistencia", "Consistência nas cinco repetições"],
  ["05_falhas", "Classes de falha"],
] as const;

const tableNames = [
  "RELATORIO.md", "units.csv", "units.jsonl", "architecture-summary.csv", "category-summary.csv", "difficulty-summary.csv",
  "scenario-metrics.csv", "scenario-measurements.csv", "measurement-distributions.csv", "paired-secondary-effects.csv",
  "paired-success.csv", "quality-distributions.csv", "critical-flags.csv", "failure-classes.csv", "historical-comparison.csv",
  "phase-cost-summary.csv", "resource-consumption.json", "provenance.json", "recheck-analysis.json", "results-summary.json",
  "scope-probe-summary.json",
] as const;
const artifacts: Readonly<Record<string, string>> = Object.freeze(Object.fromEntries([
  ...tableNames.map((name) => [name, name]),
  ...V44_FIGURES.flatMap(([name]) => ["png", "svg"].map((extension) => [`${name}.${extension}`, `figures/${name}.${extension}`])),
]));

interface Pair {
  architectureA: ComparisonArchitecture;
  architectureB: ComparisonArchitecture;
  scenarios: number;
  difference: number;
  low: number;
  high: number;
  adjustedP: number;
}

type Data = { state: "pending" } | {
  state: "ready";
  summaries: ComparisonSummary[];
  pairs: Pair[];
  resources: ResourcePhase[];
  units: number;
  scenarios: number;
  repetitions: number;
  successes: number;
  schemaValid: number;
  humanReviewPending: boolean;
  generationWorkers: number;
  judgeWorkers: number;
  waves: number;
  excludedSequentialUnits: number;
  manifestSha256: string;
  artifacts: string[];
};

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid v4.4 result record");
  return value as Record<string, unknown>;
}

function assertAdditionalPrivateFields(value: unknown): void {
  if (Array.isArray(value)) value.forEach(assertAdditionalPrivateFields);
  else if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      if (additionalPrivateFields.has(key)) throw new Error("Private v4.4 research field");
      assertAdditionalPrivateFields(child);
    }
  }
}

function parseRecord(buffer: Buffer) {
  const value = record(JSON.parse(buffer.toString("utf8")));
  assertNoPrivateFields(value);
  assertAdditionalPrivateFields(value);
  return value;
}

function finite(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value)) throw new Error("Invalid v4.4 measurement");
  return value;
}

export async function loadComparisonV44(base = RESULTS_DIRECTORY): Promise<Data> {
  try {
    const files = await inventory(base);
    const [provenance, result, consumption, unitData] = await Promise.all([
      verifiedFile(base, "provenance.json", files).then(parseRecord),
      verifiedFile(base, "results-summary.json", files).then(parseRecord),
      verifiedFile(base, "resource-consumption.json", files).then(parseRecord),
      verifiedFile(base, "units.jsonl", files),
    ]);
    const dispatch = record(provenance.generation_dispatch);
    const amendment = record(provenance.parallel_amendment);
    const manifestSha256 = provenance.manifest_sha256;
    if (provenance.protocol !== PROTOCOL || provenance.execution !== "parallel_balanced_waves" || provenance.terminal_units !== 600
        || provenance.scenario_count !== 40 || provenance.repetitions !== 5 || result.generated !== 600
        || typeof manifestSha256 !== "string" || !/^[a-f0-9]{64}$/.test(manifestSha256)
        || record(result.provenance).manifest_sha256 !== manifestSha256 || dispatch.unit_timestamp_pairs_verified !== 600
        || provenance.raw_conversations_published !== false || amendment.included_prior_sequential_units !== 0
        || !Array.isArray(result.architectures) || !Array.isArray(result.paired_success)) throw new Error("Incomplete v4.4 result export");
    const units = validateUnits(unitData.toString("utf8"));
    assertAdditionalPrivateFields(units);
    const summaries = result.architectures.map(summary);
    if (summaries.length !== 3 || new Set(summaries.map((item) => item.architecture)).size !== 3) throw new Error("Incomplete v4.4 architecture summaries");
    for (const row of summaries) {
      const selected = units.filter((unit) => unit.architecture === row.architecture);
      const taskSuccesses = selected.filter((unit) => unit.task_success === true).length;
      const technical = selected.filter((unit) => unit.success === true).length;
      const contract = selected.filter((unit) => unit.architectural_compliance === true).length;
      const schema = selected.filter((unit) => unit.judge_schema_valid === true).length;
      const applicable = selected.filter((unit) => unit.procedure_applicable === true).length;
      const compliant = selected.filter((unit) => unit.procedure_applicable === true && unit.procedure_compliance === true).length;
      if (selected.length !== row.planned || row.task_successes !== taskSuccesses || row.technical_successes !== technical
          || row.architectural_compliant !== contract || row.judge_schema_valid !== schema
          || row.mandatory_evidence_applicable !== applicable || row.mandatory_evidence_compliant !== compliant
          || row.task_unknown !== selected.filter((unit) => unit.task_success === null).length) throw new Error("v4.4 counts do not reconcile");
    }
    const pairs = result.paired_success.map((value): Pair => {
      const row = record(value);
      const architectureA = architecture(row.architecture_a), architectureB = architecture(row.architecture_b);
      const low = finite(row.bootstrap_95_low_pp), high = finite(row.bootstrap_95_high_pp);
      const adjustedP = finite(row.p_holm_three_comparisons);
      if (architectureA === architectureB || low > high || adjustedP < 0 || adjustedP > 1) throw new Error("Invalid v4.4 paired contrast");
      return { architectureA, architectureB, scenarios: count(row.paired_scenarios, 40), difference: finite(row.difference_pp_b_minus_a), low, high, adjustedP };
    });
    if (pairs.length !== 3 || pairs.some((pair) => pair.scenarios !== 40)
        || new Set(pairs.map((pair) => [pair.architectureA, pair.architectureB].sort().join("/"))).size !== 3) throw new Error("Incomplete v4.4 contrasts");
    const resources = phases.map((phase): ResourcePhase => {
      const row = record(consumption[phase]);
      const starts = count(row.requests_started, Number.MAX_SAFE_INTEGER);
      return { phase, requests_started: starts, requests_with_usage: count(row.requests_with_usage, starts),
        estimated_cost_usd: number(row.estimated_cost_usd, true),
        known_partial_estimated_cost_usd: number(row.known_partial_estimated_cost_usd, true) };
    });
    const successes = count(result.task_successes, 600), schemaValid = count(result.primary_schema_valid, 600);
    if (successes !== summaries.reduce((total, row) => total + row.task_successes, 0)
        || schemaValid !== summaries.reduce((total, row) => total + row.judge_schema_valid, 0)
        || result.human_validation_status !== "pending" || result.human_review_performed !== false) throw new Error("Invalid v4.4 overall disposition");
    const generationWorkers = count(dispatch.workers, 600), waves = count(dispatch.waves, 600);
    if (!generationWorkers || generationWorkers % 3 || waves !== Math.ceil(600 / generationWorkers)
        || dispatch.wave_barriers_verified !== waves - 1) throw new Error("Invalid v4.4 generation waves");
    return { state: "ready", summaries: COMPARISON_ARCHITECTURES.map((name) => summaries.find((row) => row.architecture === name)!),
      pairs, resources, units: 600, scenarios: 40, repetitions: 5, successes, schemaValid, humanReviewPending: true,
      generationWorkers, judgeWorkers: count(provenance.judge_workers, 600), waves,
      excludedSequentialUnits: count(amendment.prior_sequential_terminal_units_excluded, 600), manifestSha256,
      artifacts: Object.keys(artifacts).filter((name) => Object.hasOwn(files, artifacts[name])) };
  } catch {
    return { state: "pending" };
  }
}

export async function readComparisonV44Artifact(name: string, base = RESULTS_DIRECTORY) {
  if (!Object.hasOwn(artifacts, name) || (await loadComparisonV44(base)).state !== "ready") return null;
  try {
    const data = await verifiedFile(base, artifacts[name], await inventory(base));
    const extension = path.extname(name);
    if (extension === ".json") parseRecord(data);
    if (extension === ".jsonl") assertAdditionalPrivateFields(validateUnits(data.toString("utf8")));
    if (extension === ".csv") assertAdditionalPrivateFields(parseComparisonCsv(data.toString("utf8")));
    if (extension === ".md" && /bedrock-api-key-|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|\/Users\/|research-data\/private\//i.test(data.toString("utf8"))) return null;
    if (extension === ".svg" && /<script|<foreignObject|<!ENTITY|\bon\w+\s*=|(?:href|src)\s*=\s*["'](?!#|data:image\/)/i.test(data.toString("utf8"))) return null;
    if (extension === ".png" && !data.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) return null;
    const types: Record<string, string> = { ".json": "application/json; charset=utf-8", ".jsonl": "application/x-ndjson; charset=utf-8",
      ".csv": "text/csv; charset=utf-8", ".md": "text/markdown; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png" };
    return { data, contentType: types[extension] };
  } catch {
    return null;
  }
}
