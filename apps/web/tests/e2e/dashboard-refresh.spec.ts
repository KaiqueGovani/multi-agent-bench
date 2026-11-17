import { expect, test } from "@playwright/test";
import path from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { installMockEventSource, mockFrontendApi } from "./support/mock-runtime-fixtures";

const before = process.env.MAB_UI_PHASE === "before";
const evidence = path.resolve(__dirname, "../../../../research-data/local/ui-refresh");

test.beforeEach(async ({ page }) => {
  await installMockEventSource(page);
  await mockFrontendApi(page);
});

for (const viewport of [{ name: "desktop", width: 1440, height: 1000 }, { name: "mobile", width: 390, height: 844 }]) {
  test(`dashboard stays readable at ${viewport.name} width`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Dashboard operacional" })).toBeVisible();
    await expect(page.getByText("Conversas em acompanhamento", { exact: true })).toBeVisible();
    if (!before) {
      await expect(page.getByText("Monitor técnico da conversa", { exact: true })).toHaveCount(0);
      await expect(page.getByTestId("runtime-panel-technical")).toHaveCount(0);
      await expect(page.getByTestId("dashboard-latency-chart")).toBeVisible();
      await expect(page.getByTestId("dashboard-latency-chart")).toContainText("segundos");
      await expect(page.getByTestId("tool-usage-legend")).toContainText("Estoque");
      await expect(page.getByRole("heading", { name: "Arquiteturas", exact: true })).toHaveCount(0);
      await expect(page.getByRole("heading", { name: "Anexos", exact: true })).toHaveCount(0);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    }
    await page.screenshot({ path: path.join(evidence, `dashboard-${viewport.name}-${before ? "before" : "after"}.png`), fullPage: true });
  });
}

test("keeps low execution counts visible independently of latency", async ({ page }) => {
  await page.goto("/dashboard");
  const counts = page.getByTestId("architecture-run-counts");
  await expect(counts.getByRole("listitem")).toHaveCount(3);
  for (const item of await counts.getByRole("listitem").all()) await expect(item).toContainText("1");
  const paths = counts.locator("..").locator(".recharts-bar-rectangle path");
  await expect(paths).toHaveCount(3);
  for (const bar of await paths.all()) expect((await bar.boundingBox())!.height).toBeGreaterThan(30);
  await expect(page.getByLabel("Latência média por arquitetura")).toContainText("6,2 s");
});

test("keeps long tool names inside the card on a narrow screen", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 850 });
  await page.route("**/dashboard/metrics", async (route) => {
    await route.fulfill({ json: {
      generatedAt: "2026-11-17T12:00:00Z", byArchitecture: [], byModel: [], byScenario: [], byAttachmentType: [], conversations: [],
      totals: { conversations: 0, runs: 0, runsCompleted: 0, runsFailed: 0, runsHumanReview: 0, messages: 0, attachments: 0, events: 0 },
      byTool: [
        { key: "consulta_de_disponibilidade_de_medicamentos_com_nome_muito_longo", count: 3 },
        { key: "faq_lookup", count: 1 },
      ],
    } });
  });
  await page.goto("/dashboard");
  const legend = page.getByTestId("tool-usage-legend");
  await expect(legend).toContainText("75%");
  await expect(legend).toContainText("25%");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("dashboard review failures preserve the note and allow retry", async ({ page }) => {
  let attempts = 0;
  let resolved = false;
  await page.route("**/reviews/review-workflow-1/resolve", async (route) => {
    attempts += 1;
    if (attempts === 1) return route.fulfill({ status: 503, json: { detail: "Revisão temporariamente indisponível" } });
    resolved = true;
    return route.fulfill({ json: { id: "review-workflow-1", status: "resolved" } });
  });
  await page.route("**/reviews", async (route) => resolved ? route.fulfill({ json: { reviewTasks: [] } }) : route.fallback());
  await page.goto("/dashboard");
  const note = page.getByRole("textbox", { name: "Observação da revisão review-workflow-1" });
  await note.fill("Confirmado pelo farmacêutico.");
  const approve = page.getByRole("button", { name: "Aprovar", exact: true });
  await approve.click();
  await expect(page.getByTestId("dashboard-page").getByRole("alert")).toContainText("Revisão temporariamente indisponível");
  await expect(note).toHaveValue("Confirmado pelo farmacêutico.");
  await expect(approve).toBeEnabled();
  await approve.click();
  await expect(page.getByText("Nenhuma revisão aberta no momento.")).toBeVisible();
  await expect(page.getByTestId("dashboard-page").getByRole("alert")).toHaveCount(0);
  expect(attempts).toBe(2);
});

test("dashboard remains accessible without nested technical panels", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.getByText("Conversas em acompanhamento", { exact: true })).toBeVisible();
  const audit = await new AxeBuilder({ page }).analyze();
  expect(audit.violations).toEqual([]);
});
