import { expect, test } from "@playwright/test";
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const cohorts = [
  { version: "v42", directory: "agents-as-tools-v42", ready: "corrected-results-ready" },
  { version: "v44", directory: "architectural-comparison-v44", ready: "comparison-v44-ready" },
];
const figures = ["01_sucesso", "02_latencia_custo_sucesso", "03_categorias", "04_consistencia", "05_falhas"];
const evidence = path.resolve(__dirname, "../../../../research-data/local/ui-terminology");

for (const cohort of cohorts) {
  const route = `/research/comparison-${cohort.version}`;

  test(`${cohort.version} uses Orquestrador in research labels and all published chart formats`, async ({ page, request }) => {
    await page.goto(route);
    await expect(page.getByTestId(cohort.ready)).toBeVisible();
    await expect(page.getByRole("heading", { name: "Orquestrador + especialistas", exact: true }).first()).toBeVisible();
    expect(await page.locator("main").innerText()).not.toMatch(/\bsupervisor(?:es)?\b/i);

    const base = path.resolve(__dirname, "../../../../research-data/results", cohort.directory);
    const inventory = JSON.parse(fs.readFileSync(path.join(base, "FILES.json"), "utf8"));
    for (const figure of figures) {
      const svg = await request.get(`${route}/files/${figure}.svg`);
      expect(svg.ok(), figure).toBe(true);
      const markup = await svg.text();
      expect(markup).toContain("Orquestrador");
      expect(markup).not.toMatch(/\bsupervisor(?:es)?\b/i);
      for (const extension of ["svg", "png"]) {
        const response = extension === "svg" ? svg : await request.get(`${route}/files/${figure}.${extension}`);
        expect(response.ok(), `${figure}.${extension}`).toBe(true);
        const bytes = await response.body();
        const expected = inventory[`figures/${figure}.${extension}`];
        expect(bytes.length).toBe(expected.bytes);
        expect(createHash("sha256").update(bytes).digest("hex")).toBe(expected.sha256);
      }
    }
    // Public scientific identifiers retain the original recorded role names.
    // Display wording must not mutate the provenance or any quantitative table.
    for (const name of ["provenance.json", "architecture-summary.csv", "units.jsonl"]) {
      const response = await request.get(`${route}/files/${name}`);
      expect(response.ok(), name).toBe(true);
      const data = await response.body();
      expect(createHash("sha256").update(data).digest("hex")).toBe(inventory[name].sha256);
      if (name === "provenance.json" && cohort.version === "v42") expect(data.toString("utf8")).toContain('"supervisor"');
    }

    fs.mkdirSync(evidence, { recursive: true });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.screenshot({ path: path.join(evidence, `research-${cohort.version}-desktop.png`), fullPage: true });
    const image = page.getByRole("img", { name: /Latência do coletor, custo e sucesso/ });
    await image.scrollIntoViewIfNeeded();
    await expect.poll(() => image.evaluate((node) => (node as HTMLImageElement).complete && (node as HTMLImageElement).naturalWidth > 0)).toBe(true);
    await image.screenshot({ path: path.join(evidence, `research-${cohort.version}-latency-chart.png`) });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(evidence, `research-${cohort.version}-mobile.png`), fullPage: true });
  });
}

test("research landing links keep the unified wording in its published destinations", async ({ page }) => {
  await page.goto("/research");
  await expect(page.getByRole("link", { name: "Resultados v4.4", exact: true })).toBeVisible();
  expect(await page.locator("body").innerText()).not.toMatch(/\bsupervisor(?:es)?\b/i);
});
