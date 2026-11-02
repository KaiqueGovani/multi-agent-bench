// Server-side only: this module reads the sanitized quantitative export, never raw research records.
import { createHash } from "node:crypto";
import { lstat, readFile, realpath } from "node:fs/promises";
import path from "node:path";

export const COMPARISON_ARCHITECTURES = ["centralized_orchestration", "structured_workflow", "decentralized_swarm"] as const;
export type ComparisonArchitecture = typeof COMPARISON_ARCHITECTURES[number];
export const CORRECTED_RESULTS_DIRECTORY = path.resolve(process.cwd(), "../../research-data/results/agents-as-tools-v42");
const HISTORICAL_SUMMARY = path.resolve(process.cwd(), "../../research-data/results/matrix40-v1-final/architecture-summary.csv");

const figureNames = ["01_sucesso", "02_latencia_custo_sucesso", "03_categorias", "04_consistencia", "05_falhas"] as const;
const tableNames = ["units.csv", "units.jsonl", "architecture-summary.csv", "category-summary.csv", "difficulty-summary.csv", "scenario-metrics.csv", "measurement-distributions.csv", "paired-secondary-effects.csv", "paired-success.csv", "quality-distributions.csv", "critical-flags.csv", "failure-classes.csv", "historical-comparison.csv", "trajectory-examples-metadata.csv", "resource-consumption.json", "provenance.json", "recheck-analysis.json", "results-summary.json"] as const;
export const PUBLIC_COMPARISON_ARTIFACTS: Readonly<Record<string, string>> = Object.freeze(Object.fromEntries([
  ...tableNames.map((name) => [name, name]),
  ...figureNames.flatMap((name) => ["svg", "png"].map((extension) => [`${name}.${extension}`, `figures/${name}.${extension}`])),
]));

export interface ComparisonSummary {
  architecture: ComparisonArchitecture;
  planned: number;
  technical_successes: number;
  architectural_compliant: number;
  architectural_violations: number;
  architectural_unknown: number;
  task_successes: number;
  task_failures: number;
  task_unknown: number;
  content_successes: number;
  content_evaluable: number;
  mandatory_evidence_applicable: number;
  mandatory_evidence_compliant: number;
  mandatory_evidence_evaluable: number;
  judge_schema_valid: number;
  judge_internally_inconsistent: number;
  judge_valid_assessment: number;
  judge_invalid_or_missing: number;
  latency_ms_median_of_case_medians: number | null;
  end_to_end_latency_ms_median_of_case_medians: number | null;
  estimated_generation_cost_usd: number | null;
  estimated_cost_per_observed_task_success_usd: number | null;
}

export interface HistoricalSummary {
  architecture: ComparisonArchitecture;
  planned: number;
  task_successes: number;
  task_unknown: number;
}

export interface ResourcePhase {
  phase: string;
  requests_started: number;
  requests_with_usage: number;
  estimated_cost_usd: number | null;
  known_partial_estimated_cost_usd: number | null;
}

export type CorrectedComparisonData = { state: "pending" } | {
  state: "ready";
  protocol: "architectural-comparison-v4.2";
  experimentId: string;
  commit: string;
  manifestSha256: string;
  summaries: ComparisonSummary[];
  historical: HistoricalSummary[];
  resources: ResourcePhase[];
  pricing: { currency: string; region: string; checkedOn: string };
  artifacts: string[];
};

type JsonRecord = Record<string, unknown>;
type Inventory = Record<string, { sha256: string; bytes: number }>;
const privateField = /^(?:final_text|finalText|inputText|outputText|contentText|text|request|response|responses|messages|history|attachments|expected_result|expected_facts|essential_requirements|required_evidence|optional_evidence|domain_evidence|unsupported_claims|prohibited_behaviors|critical_restrictions|reference|gold|evaluation|criteria|arguments|payload|callback|reason|rationale|phone|email|api.?key|.*(?:secret|credential|authorization|bearer|cookie).*|retrieval.?url|storage.?key)$/i;
const credentialValue = /bedrock-api-key-|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b/i;
// Canonical SHA-256 of the public, frozen v4.2 snapshots. These exact static
// metadata blocks contain role names such as "attachments" and a historical
// comparison policy named "history"; neither is realized conversation data.
// No other artifact/path receives this exception, and any changed value or
// additional field changes the digest and is rejected.
const approvedProvenanceMetadata: Readonly<Record<string, string>> = {
  configuration: "2d4de251f757ac9e468aa5994f2039c3861a335d746fe20750f048c84bc96469",
  analysis_plan: "9a014c0d4aedad6f11a351a1b236ddcb34cc8b8ffbb712fc51b62f2325ed49b1",
};

function object(value: unknown): JsonRecord {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid quantitative artifact");
  return value as JsonRecord;
}

function canonicalValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonicalValue);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([key, child]) => [key, canonicalValue(child)]));
  return value;
}

function assertNoPrivateFields(value: unknown, artifactName?: string, trail: string[] = []): void {
  const approved = artifactName === "provenance.json" && trail.length === 1 ? approvedProvenanceMetadata[trail[0]] : undefined;
  if (approved) {
    if (createHash("sha256").update(JSON.stringify(canonicalValue(value))).digest("hex") !== approved) throw new Error("Static provenance metadata differs from the frozen public definition");
    return;
  }
  if (typeof value === "string" && credentialValue.test(value)) throw new Error("Credential-shaped value is not a public artifact");
  else if (Array.isArray(value)) value.forEach((child, index) => assertNoPrivateFields(child, artifactName, [...trail, String(index)]));
  else if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      if (privateField.test(key)) throw new Error("Private research fields are not public artifacts");
      assertNoPrivateFields(child, artifactName, [...trail, key]);
    }
  }
}

async function boundedFile(base: string, relative: string): Promise<Buffer> {
  const baseStat = await lstat(base);
  if (!baseStat.isDirectory() || baseStat.isSymbolicLink()) throw new Error("Invalid public export directory");
  const target = path.join(base, relative);
  const stat = await lstat(target);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size > 24 * 1024 * 1024) throw new Error("Invalid public export file");
  const [resolvedBase, resolvedTarget] = await Promise.all([realpath(base), realpath(target)]);
  if (!resolvedTarget.startsWith(resolvedBase + path.sep)) throw new Error("Artifact leaves the public export directory");
  return readFile(target);
}

async function inventory(base: string): Promise<Inventory> {
  const parsed = object(JSON.parse((await boundedFile(base, "FILES.json")).toString("utf8")));
  const result: Inventory = {};
  for (const [name, value] of Object.entries(parsed)) {
    const entry = object(value);
    if (typeof entry.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(entry.sha256) || !Number.isInteger(entry.bytes) || (entry.bytes as number) < 0) throw new Error("Invalid artifact inventory");
    result[name] = { sha256: entry.sha256, bytes: entry.bytes as number };
  }
  return result;
}

async function verifiedFile(base: string, relative: string, files: Inventory): Promise<Buffer> {
  const entry = files[relative];
  if (!entry) throw new Error("Artifact is absent from the final inventory");
  const data = await boundedFile(base, relative);
  if (data.length !== entry.bytes || createHash("sha256").update(data).digest("hex") !== entry.sha256) throw new Error("Artifact integrity check failed");
  return data;
}

export function parseComparisonCsv(text: string): Record<string, string>[] {
  const records: string[][] = [];
  let record: string[] = [], value = "", quoted = false;
  for (let index = 0; index < text.length; index++) {
    const char = text[index];
    if (char === '"') {
      if (quoted && text[index + 1] === '"') { value += '"'; index++; }
      else quoted = !quoted;
    } else if (char === "," && !quoted) { record.push(value); value = ""; }
    else if (char === "\n" && !quoted) { record.push(value.replace(/\r$/, "")); records.push(record); record = []; value = ""; }
    else value += char;
  }
  if (quoted) throw new Error("Unterminated CSV quote");
  if (value || record.length) { record.push(value.replace(/\r$/, "")); records.push(record); }
  const headers = records.shift() ?? [];
  if (!headers.length || new Set(headers).size !== headers.length || headers.some((header) => privateField.test(header))) throw new Error("Invalid public CSV fields");
  return records.filter((values) => values.some(Boolean)).map((values) => {
    if (values.length !== headers.length) throw new Error("Invalid public CSV row");
    if (values.some((item) => credentialValue.test(item))) throw new Error("Credential-shaped CSV value");
    return Object.fromEntries(headers.map((header, index) => [header, values[index]]));
  });
}

function number(value: unknown, nullable = false): number | null {
  if (nullable && value === null) return null;
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) throw new Error("Invalid quantitative measurement");
  return value;
}

function count(value: unknown, maximum = 200): number {
  const result = number(value);
  if (!Number.isInteger(result) || result! > maximum) throw new Error("Invalid quantitative denominator");
  return result!;
}

function architecture(value: unknown): ComparisonArchitecture {
  if (!COMPARISON_ARCHITECTURES.includes(value as ComparisonArchitecture)) throw new Error("Invalid architecture");
  return value as ComparisonArchitecture;
}

function summary(value: unknown): ComparisonSummary {
  const source = object(value);
  const result: JsonRecord = { architecture: architecture(source.architecture) };
  const fields = ["planned", "technical_successes", "architectural_compliant", "architectural_violations", "architectural_unknown", "task_successes", "task_failures", "task_unknown", "content_successes", "content_evaluable", "mandatory_evidence_applicable", "mandatory_evidence_compliant", "mandatory_evidence_evaluable", "judge_schema_valid", "judge_internally_inconsistent", "judge_valid_assessment", "judge_invalid_or_missing"];
  fields.forEach((field) => { result[field] = count(source[field]); });
  ["latency_ms_median_of_case_medians", "end_to_end_latency_ms_median_of_case_medians", "estimated_generation_cost_usd", "estimated_cost_per_observed_task_success_usd"].forEach((field) => { result[field] = number(source[field], true); });
  const typed = result as unknown as ComparisonSummary;
  if (typed.planned !== 200 || typed.task_successes + typed.task_failures + typed.task_unknown !== 200 || typed.architectural_compliant + typed.architectural_violations + typed.architectural_unknown !== 200 || typed.judge_valid_assessment + typed.judge_invalid_or_missing !== 200 || typed.content_successes > typed.content_evaluable || typed.mandatory_evidence_compliant > typed.mandatory_evidence_evaluable || typed.mandatory_evidence_evaluable > typed.mandatory_evidence_applicable) throw new Error("Unreconciled result denominators");
  return typed;
}

function validateUnits(text: string): JsonRecord[] {
  const units = text.trim().split("\n").filter(Boolean).map((line) => object(JSON.parse(line)));
  const combinations = new Set<string>(), unitIds = new Set<string>();
  const scenarios = new Map<string, number>();
  for (const unit of units) {
    assertNoPrivateFields(unit);
    ["success", "architectural_compliance", "task_success", "content_success", "procedure_applicable", "procedure_compliance"].forEach((field) => {
      if (unit[field] !== null && typeof unit[field] !== "boolean") throw new Error("Invalid public unit outcome");
    });
    if (Object.values(unit).some((value) => value !== null && !["string", "number", "boolean"].includes(typeof value))) throw new Error("Unit contains non-scalar research data");
    if (typeof unit.scenario_id !== "string" || !/^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,159}$/.test(unit.scenario_id) || typeof unit.unit_id !== "string" || !/^[a-f0-9-]{36}$/.test(unit.unit_id)) throw new Error("Invalid public unit identifiers");
    const arch = architecture(unit.architecture);
    if (!Number.isInteger(unit.repetition) || (unit.repetition as number) < 0 || (unit.repetition as number) > 4) throw new Error("Invalid repetition");
    combinations.add(JSON.stringify([unit.scenario_id, arch, unit.repetition]));
    unitIds.add(unit.unit_id);
    scenarios.set(unit.scenario_id, (scenarios.get(unit.scenario_id) ?? 0) + 1);
  }
  if (units.length !== 600 || combinations.size !== 600 || unitIds.size !== 600 || scenarios.size !== 40 || [...scenarios.values()].some((value) => value !== 15)) throw new Error("Require all 600 unique planned units");
  return units;
}

async function loadHistorical(file: string): Promise<HistoricalSummary[]> {
  try {
    const rows = parseComparisonCsv(await readFile(file, "utf8")).map((row) => ({ architecture: architecture(row.architecture), planned: count(Number(row.planned)), task_successes: count(Number(row.task_successes)), task_unknown: count(Number(row.task_unknown)) }));
    if (rows.length !== 3 || new Set(rows.map((row) => row.architecture)).size !== 3 || rows.some((row) => row.planned !== 200)) return [];
    return COMPARISON_ARCHITECTURES.map((arch) => rows.find((row) => row.architecture === arch)!);
  } catch { return []; }
}

/** Injectable file roots are for fixture tests; production callers use only fixed public roots. */
export async function loadCorrectedComparison(base = CORRECTED_RESULTS_DIRECTORY, historicalFile = HISTORICAL_SUMMARY): Promise<CorrectedComparisonData> {
  try {
    const files = await inventory(base);
    const required = ["provenance.json", "results-summary.json", "resource-consumption.json", "units.jsonl", ...figureNames.flatMap((name) => ["svg", "png"].map((extension) => `figures/${name}.${extension}`))];
    const buffers = await Promise.all(required.map((name) => verifiedFile(base, name, files)));
    const provenance = object(JSON.parse(buffers[0].toString("utf8")));
    const results = object(JSON.parse(buffers[1].toString("utf8")));
    const consumption = object(JSON.parse(buffers[2].toString("utf8")));
    if (!Object.hasOwn(provenance, "configuration") || !Object.hasOwn(provenance, "analysis_plan")) throw new Error("Missing frozen static provenance metadata");
    assertNoPrivateFields(provenance, "provenance.json");
    assertNoPrivateFields(results);
    assertNoPrivateFields(consumption);
    if (provenance.protocol !== "architectural-comparison-v4.2" || provenance.units !== 600 || provenance.unique_combinations !== 600 || results.generated !== 600 || typeof provenance.commit !== "string" || !/^[a-f0-9]{40}$/.test(provenance.commit) || typeof provenance.manifest_sha256 !== "string" || !/^[a-f0-9]{64}$/.test(provenance.manifest_sha256) || typeof provenance.experiment_id !== "string" || !/^[a-zA-Z0-9_.-]{1,160}$/.test(provenance.experiment_id)) throw new Error("Unverified corrected cohort");
    const units = validateUnits(buffers[3].toString("utf8"));
    if (!Array.isArray(results.architectures)) throw new Error("Missing complete architecture summaries");
    const summaries = results.architectures.map(summary);
    if (summaries.length !== 3 || new Set(summaries.map((item) => item.architecture)).size !== 3) throw new Error("Incomplete architecture comparison");
    for (const item of summaries) {
      const rows = units.filter((unit) => unit.architecture === item.architecture);
      const checks: [number, number][] = [
        [item.technical_successes, rows.filter((row) => row.success === true).length],
        [item.architectural_compliant, rows.filter((row) => row.architectural_compliance === true).length],
        [item.architectural_violations, rows.filter((row) => row.architectural_compliance === false).length],
        [item.architectural_unknown, rows.filter((row) => row.architectural_compliance === null).length],
        [item.task_successes, rows.filter((row) => row.task_success === true).length],
        [item.task_failures, rows.filter((row) => row.task_success === false).length],
        [item.task_unknown, rows.filter((row) => row.task_success === null).length],
        [item.content_successes, rows.filter((row) => row.content_success === true).length],
        [item.content_evaluable, rows.filter((row) => row.content_success !== null).length],
        [item.mandatory_evidence_applicable, rows.filter((row) => row.procedure_applicable === true).length],
        [item.mandatory_evidence_compliant, rows.filter((row) => row.procedure_applicable === true && row.procedure_compliance === true).length],
        [item.mandatory_evidence_evaluable, rows.filter((row) => row.procedure_applicable === true && row.procedure_compliance !== null).length],
      ];
      if (rows.length !== 200 || checks.some(([reported, observed]) => reported !== observed)) throw new Error("Summary does not reconcile with public units");
    }
    const resources = ["generation", "judgment", "recheck", "engineering_pilot", "engineering_pilot_judgment", "api_integration"].filter((phase) => consumption[phase] !== undefined).map((phase) => {
      const row = object(consumption[phase]);
      return { phase, requests_started: count(row.requests_started, Number.MAX_SAFE_INTEGER), requests_with_usage: count(row.requests_with_usage, Number.MAX_SAFE_INTEGER), estimated_cost_usd: number(row.estimated_cost_usd, true), known_partial_estimated_cost_usd: number(row.known_partial_estimated_cost_usd, true) };
    });
    const pricing = object(consumption.pricing);
    if (pricing.currency !== "USD" || typeof pricing.region !== "string" || !/^[a-z0-9-]{1,32}$/.test(pricing.region) || typeof pricing.checked_on !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(pricing.checked_on)) throw new Error("Missing estimated-cost provenance");
    return { state: "ready", protocol: "architectural-comparison-v4.2", experimentId: provenance.experiment_id, commit: provenance.commit, manifestSha256: provenance.manifest_sha256, summaries: COMPARISON_ARCHITECTURES.map((arch) => summaries.find((item) => item.architecture === arch)!), historical: await loadHistorical(historicalFile), resources, pricing: { currency: "USD", region: pricing.region, checkedOn: pricing.checked_on }, artifacts: Object.keys(PUBLIC_COMPARISON_ARTIFACTS).filter((name) => files[PUBLIC_COMPARISON_ARTIFACTS[name]]) };
  } catch { return { state: "pending" }; }
}

/** A fixed whitelist, completed-cohort gate and verified inventory protect each read. */
export async function readCorrectedComparisonArtifact(name: string, base = CORRECTED_RESULTS_DIRECTORY): Promise<{ data: Buffer; contentType: string } | null> {
  if (!Object.hasOwn(PUBLIC_COMPARISON_ARTIFACTS, name)) return null;
  if ((await loadCorrectedComparison(base)).state !== "ready") return null;
  try {
    const data = await verifiedFile(base, PUBLIC_COMPARISON_ARTIFACTS[name], await inventory(base));
    const extension = path.extname(name);
    if (extension === ".json") assertNoPrivateFields(JSON.parse(data.toString("utf8")), name);
    if (extension === ".jsonl") data.toString("utf8").trim().split("\n").filter(Boolean).forEach((line) => assertNoPrivateFields(JSON.parse(line)));
    if (extension === ".csv") parseComparisonCsv(data.toString("utf8"));
    if (extension === ".svg" && /<script|<foreignObject|<!ENTITY|\bon\w+\s*=|(?:href|src)\s*=\s*["'](?!#|data:image\/)/i.test(data.toString("utf8"))) return null;
    if (extension === ".png" && !data.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) return null;
    const types: Record<string, string> = { ".json": "application/json; charset=utf-8", ".jsonl": "application/x-ndjson; charset=utf-8", ".csv": "text/csv; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png" };
    return { data, contentType: types[extension] };
  } catch { return null; }
}
