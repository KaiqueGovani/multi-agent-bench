import { expect, test } from "@playwright/test";
import { createHash, randomUUID } from "node:crypto";
import { mkdtemp, mkdir, readFile, rm, symlink, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { CorrectedComparisonView } from "../../src/components/runtime/corrected-comparison-view";
import { COMPARISON_ARCHITECTURES, loadCorrectedComparison, parseComparisonCsv, readCorrectedComparisonArtifact } from "../../src/lib/corrected-comparison/results";
import type { CorrectedComparisonData } from "../../src/lib/corrected-comparison/results";

const temporary: string[] = [];
const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a2ioAAAAASUVORK5CYII=", "base64");

// Playwright serializes imported TSX into descriptors. Restore those native-tag
// descriptors for React's server renderer without adding a fixture route or
// allowing the production loader to point at arbitrary directories.
function reactTree(value: unknown, fallbackKey?: string): React.ReactNode {
  if (Array.isArray(value)) return value.map((item, index) => reactTree(item, String(index)));
  if (value && typeof value === "object" && "__pw_type" in value) {
    const node = value as unknown as { type: string; props: Record<string, unknown>; key?: string };
    return React.createElement(typeof node.type === "string" ? node.type : React.Fragment, { ...node.props, key: node.key ?? fallbackKey, children: reactTree(node.props.children) });
  }
  return value as React.ReactNode;
}
function viewMarkup(data: CorrectedComparisonData) {
  return renderToStaticMarkup(reactTree(CorrectedComparisonView({ data })));
}

async function indexedWrite(base: string, name: string, value: string | Buffer) {
  const data = Buffer.isBuffer(value) ? value : Buffer.from(value);
  await mkdir(path.dirname(path.join(base, name)), { recursive: true });
  await writeFile(path.join(base, name), data);
  const file = path.join(base, "FILES.json");
  const inventory = JSON.parse(await readFile(file, "utf8").catch(() => "{}"));
  inventory[name] = { sha256: createHash("sha256").update(data).digest("hex"), bytes: data.length };
  await writeFile(file, JSON.stringify(inventory));
}

async function fixture() {
  const base = await mkdtemp(path.join(os.tmpdir(), "SYNTHETIC-corrected-public-export-"));
  temporary.push(base);
  const summaries = COMPARISON_ARCHITECTURES.map((architecture, index) => ({
    architecture, planned: 200, technical_successes: 190,
    architectural_compliant: 190, architectural_violations: 5, architectural_unknown: 5,
    task_successes: 150, task_failures: 40, task_unknown: 10,
    content_successes: 140, content_evaluable: 190,
    mandatory_evidence_applicable: 95, mandatory_evidence_compliant: 90, mandatory_evidence_evaluable: 94,
    judge_schema_valid: 195, judge_internally_inconsistent: 5, judge_valid_assessment: 190, judge_invalid_or_missing: 10,
    latency_ms_median_of_case_medians: 1000 + index, end_to_end_latency_ms_median_of_case_medians: 1200 + index,
    estimated_generation_cost_usd: index === 1 ? null : 1.25,
    estimated_cost_per_observed_task_success_usd: index === 1 ? null : 0.008,
  }));
  const units = COMPARISON_ARCHITECTURES.flatMap((architecture) => Array.from({ length: 200 }, (_, n) => ({
    unit_id: randomUUID(), scenario_id: `SYNTHETIC-${String(Math.floor(n / 5)).padStart(2, "0")}`,
    architecture, repetition: n % 5, success: n < 190,
    architectural_compliance: n < 190 ? true : n < 195 ? false : null,
    task_success: n < 150 ? true : n < 190 ? false : null,
    content_success: n < 140 ? true : n < 190 ? false : null,
    procedure_applicable: n < 95,
    procedure_compliance: n < 90 ? true : n < 94 ? false : null,
  })));
  await indexedWrite(base, "units.jsonl", units.map((unit) => JSON.stringify(unit)).join("\n") + "\n");
  await indexedWrite(base, "units.csv", "unit_id,architecture,task_success\nsynthetic,centralized_orchestration,True\n");
  await indexedWrite(base, "results-summary.json", JSON.stringify({ generated: 600, architectures: summaries }));
  // Match the actual export's static metadata, including role-key attachments
  // and analysis_plan.history. Only responses/outcomes in this fixture are synthetic.
  const configuration = JSON.parse(await readFile(path.resolve(process.cwd(), "../../experiments/architectural-comparison-v42/static-definition.json"), "utf8")).configuration;
  const analysisPlan = JSON.parse(await readFile(path.resolve(process.cwd(), "../../experiments/architectural-comparison-v42/analysis-plan.json"), "utf8"));
  await indexedWrite(base, "provenance.json", JSON.stringify({ protocol: "architectural-comparison-v4.2", units: 600, unique_combinations: 600, commit: "a".repeat(40), manifest_sha256: "b".repeat(64), experiment_id: "synthetic-fixture-only", cases_sha256: "c".repeat(64), dependencies: { python: "synthetic" }, configuration, analysis_plan: analysisPlan, source_sha256: "d".repeat(64), exported_at: "2026-11-02T20:00:00Z", human_review_performed: false, raw_conversations_published: false }));
  await indexedWrite(base, "resource-consumption.json", JSON.stringify({ generation: { requests_started: 600, requests_with_usage: 599, estimated_cost_usd: null, known_partial_estimated_cost_usd: 1.25 }, pricing: { currency: "USD", region: "us-west-2", checked_on: "2026-11-02" } }));
  for (const name of ["01_sucesso", "02_latencia_custo_sucesso", "03_categorias", "04_consistencia", "05_falhas"]) {
    await indexedWrite(base, `figures/${name}.png`, png);
    await indexedWrite(base, `figures/${name}.svg`, '<svg xmlns="http://www.w3.org/2000/svg"><text>Synthetic figure only</text></svg>');
  }
  const historical = path.join(base, "SYNTHETIC-historical-summary.csv");
  await writeFile(historical, "architecture,planned,task_successes,task_unknown\n" + COMPARISON_ARCHITECTURES.map((architecture) => `${architecture},200,123,0`).join("\n") + "\n");
  return { base, historical, units };
}

test.afterEach(async () => { await Promise.all(temporary.splice(0).map((folder) => rm(folder, { recursive: true, force: true }))); });

test("missing final inventory shows pending without provisional values or downloads", async ({ page }) => {
  const data = { state: "pending" as const };
  await page.setContent(viewMarkup(data));
  await expect(page.getByTestId("corrected-results-pending")).toBeVisible();
  await expect(page.getByRole("table")).toHaveCount(0);
  await expect(page.locator('a[href*="/files/"]')).toHaveCount(0);
  const { base, historical } = await fixture();
  await rm(path.join(base, "FILES.json"));
  expect(await loadCorrectedComparison(base, historical)).toEqual({ state: "pending" });
  expect(await readCorrectedComparisonArtifact("units.csv", base)).toBeNull();
});

test("complete synthetic public export renders explicit denominators and separated single-agent history", async ({ page }) => {
  const { base, historical } = await fixture();
  const data = await loadCorrectedComparison(base, historical);
  expect(data.state).toBe("ready");
  expect((await readCorrectedComparisonArtifact("provenance.json", base))?.contentType).toBe("application/json; charset=utf-8");
  await page.setContent(viewMarkup(data));
  await expect(page.getByTestId("corrected-results-ready")).toContainText("600 unidades únicas verificadas");
  await expect(page.getByText("150/200", { exact: true })).toHaveCount(3);
  await expect(page.getByRole("cell").filter({ hasText: /^140\/190/ })).toHaveCount(3);
  await expect(page.getByRole("cell").filter({ hasText: /^90\/95/ })).toHaveCount(3);
  await expect(page.getByText("Centralizada histórica · agente único", { exact: true })).toBeVisible();
  await expect(page.getByText("123/200", { exact: true })).toHaveCount(3);
  await expect(page.getByText(/não atribui efeito causal/)).toBeVisible();
  await expect(page.getByText(/não representam latência de produção/)).toBeVisible();
  await expect(page.getByText("N/D", { exact: true })).toHaveCount(3);
  await expect(page.locator('a[href*="events.jsonl"],a[href*="manifest.json"]')).toHaveCount(0);
});

test("a partial, duplicate or contradictory unit export never publishes numbers", async () => {
  for (const mode of ["partial", "duplicate", "summary-disagrees"]) {
    const { base, historical, units } = await fixture();
    if (mode === "partial") units.pop();
    if (mode === "duplicate") units[599] = { ...units[0], unit_id: randomUUID() };
    if (mode === "summary-disagrees") units[0].task_success = false;
    await indexedWrite(base, "units.jsonl", units.map((unit) => JSON.stringify(unit)).join("\n"));
    expect(await loadCorrectedComparison(base, historical), mode).toEqual({ state: "pending" });
  }
});

test("inventoried provenance and file hashes are mandatory", async () => {
  const { base, historical } = await fixture();
  await writeFile(path.join(base, "results-summary.json"), '{"generated":600}');
  expect(await loadCorrectedComparison(base, historical)).toEqual({ state: "pending" });
  const other = await fixture();
  await indexedWrite(other.base, "provenance.json", JSON.stringify({ protocol: "architectural-comparison-v4.1", units: 600, unique_combinations: 600 }));
  expect(await loadCorrectedComparison(other.base, other.historical)).toEqual({ state: "pending" });
});

test("download whitelist denies private names, paths, raw fields and credentials", async () => {
  const { base } = await fixture();
  for (const name of ["events.jsonl", "responses.jsonl", "aggregated-evaluations.jsonl", "manifest.json", "blind-responses.json", "../../private/events.jsonl", "../units.csv", "__proto__"]) {
    expect(await readCorrectedComparisonArtifact(name, base), name).toBeNull();
  }
  expect((await readCorrectedComparisonArtifact("units.csv", base))?.contentType).toBe("text/csv; charset=utf-8");
  await indexedWrite(base, "units.csv", "unit_id,final_text\nsynthetic,PRIVATE_TEXT_SENTINEL\n");
  expect(await readCorrectedComparisonArtifact("units.csv", base)).toBeNull();
  await indexedWrite(base, "recheck-analysis.json", JSON.stringify({ history: ["PRIVATE_TEXT_SENTINEL"] }));
  expect(await readCorrectedComparisonArtifact("recheck-analysis.json", base)).toBeNull();
  await indexedWrite(base, "recheck-analysis.json", JSON.stringify({ aiServiceSecret: "PRIVATE_SECRET_SENTINEL" }));
  expect(await readCorrectedComparisonArtifact("recheck-analysis.json", base)).toBeNull();
});

test("private fields in unit JSON make the whole new cohort unavailable", async () => {
  const { base, historical, units } = await fixture();
  await indexedWrite(base, "units.jsonl", units.map((unit) => JSON.stringify({ ...unit, final_text: "PRIVATE_TEXT_SENTINEL" })).join("\n"));
  expect(await loadCorrectedComparison(base, historical)).toEqual({ state: "pending" });
});

test("only exact frozen static metadata is allowed at the two provenance paths", async () => {
  for (const mode of ["history-string", "history-array", "role-prompt", "hash-map", "extra-private-key", "missing-config"]) {
    const { base, historical } = await fixture();
    const provenance = JSON.parse(await readFile(path.join(base, "provenance.json"), "utf8"));
    if (mode === "history-string") provenance.analysis_plan.history = "PRIVATE_CONVERSATION_SENTINEL";
    if (mode === "history-array") provenance.analysis_plan.history = ["PRIVATE_CONVERSATION_SENTINEL"];
    if (mode === "role-prompt") provenance.configuration.role_prompts.attachments = "PRIVATE_CONVERSATION_SENTINEL";
    if (mode === "hash-map") provenance.configuration.tool_schema_hashes.attachments = "PRIVATE_CONVERSATION_SENTINEL";
    if (mode === "extra-private-key") provenance.configuration.history = ["PRIVATE_CONVERSATION_SENTINEL"];
    if (mode === "missing-config") delete provenance.configuration;
    await indexedWrite(base, "provenance.json", JSON.stringify(provenance));
    expect(await loadCorrectedComparison(base, historical), mode).toEqual({ state: "pending" });
    expect(await readCorrectedComparisonArtifact("provenance.json", base), mode).toBeNull();
  }
  const { base } = await fixture();
  const approved = JSON.parse(await readFile(path.join(base, "provenance.json"), "utf8"));
  await indexedWrite(base, "recheck-analysis.json", JSON.stringify({ configuration: approved.configuration, analysis_plan: approved.analysis_plan }));
  expect(await readCorrectedComparisonArtifact("recheck-analysis.json", base)).toBeNull();
});

test("public paths reject symlinks and active SVG content", async () => {
  const { base } = await fixture();
  const privateFile = path.join(base, "PRIVATE-NOT-SERVED.csv");
  await writeFile(privateFile, "unit_id,architecture\nprivate,private\n");
  const data = await readFile(privateFile);
  await indexedWrite(base, "units.csv", data);
  await rm(path.join(base, "units.csv"));
  await symlink(privateFile, path.join(base, "units.csv"));
  expect(await readCorrectedComparisonArtifact("units.csv", base)).toBeNull();
  await indexedWrite(base, "figures/01_sucesso.svg", '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>');
  expect(await readCorrectedComparisonArtifact("01_sucesso.svg", base)).toBeNull();
});

test("CSV parsing preserves quoted values and rejects malformed or private headers", () => {
  expect(parseComparisonCsv('metric,value\n"known, partial",1\n')).toEqual([{ metric: "known, partial", value: "1" }]);
  expect(() => parseComparisonCsv('metric,value\n"unterminated,1')).toThrow();
  expect(() => parseComparisonCsv('metric,history\nprivate,private\n')).toThrow();
});
