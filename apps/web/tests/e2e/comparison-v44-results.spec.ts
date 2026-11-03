import { expect, test } from "@playwright/test";

const pagePath = "/research/comparison-v44";

test("opens the verified v4.4 cohort from the research page", async ({ page }) => {
  await page.goto("/research");
  await page.getByRole("link", { name: "Resultados v4.4" }).click();
  await expect(page).toHaveURL(new RegExp(`${pagePath}$`));
  await expect(page.getByRole("heading", { name: "Comparação arquitetural v4.4" })).toBeVisible();
  const results = page.getByTestId("comparison-v44-ready");
  await expect(results.getByText("600 execuções únicas")).toBeVisible();
  for (const value of ["126/200", "121/200", "114/200", "Revisão humana pendente"]) {
    await expect(results.getByText(value, { exact: true })).toBeVisible();
  }
  await expect(page.getByText("13 ondas de até 48 processos", { exact: false })).toBeVisible();
  await expect(page.getByRole("table", { name: "Diferenças de sucesso e intervalos marginais de 95% em pontos percentuais" }).getByRole("row")).toHaveCount(4);
  await expect(page.getByRole("img", { name: "Sucesso observado por arquitetura" })).toHaveAttribute("src", `${pagePath}/files/01_sucesso.png`);
});

test("serves sanitized cohort files and denies private filenames", async ({ request }) => {
  const units = await request.get(`${pagePath}/files/units.jsonl`);
  expect(units.ok()).toBe(true);
  const rows = (await units.text()).trim().split("\n").map((line) => JSON.parse(line));
  expect(rows).toHaveLength(600);
  expect(new Set(rows.map((row) => `${row.scenario_id}/${row.architecture}/${row.repetition}`)).size).toBe(600);
  expect(rows.every((row) => !("final_text" in row) && !("candidate_text" in row) && !("attempt_id" in row))).toBe(true);

  for (const [name, type] of [["01_sucesso.png", "image/png"], ["01_sucesso.svg", "image/svg+xml"], ["RELATORIO.md", "text/markdown"], ["units.csv", "text/csv"]]) {
    const response = await request.get(`${pagePath}/files/${name}`);
    expect(response.ok(), name).toBe(true);
    expect(response.headers()["content-type"]).toContain(type);
  }
  for (const name of ["manifest.json", "events.jsonl", "blind-mapping.json", "__proto__"]) {
    expect((await request.get(`${pagePath}/files/${name}`)).status(), name).toBe(404);
  }
});
