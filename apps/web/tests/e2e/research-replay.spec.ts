import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
const evidence = path.resolve(
  __dirname,
  "../../../../research-data/local/auditoria-ui-20261012/depois",
);
const source = path.resolve(
  process.env.MAB_REPLAY_SOURCE ??
    path.resolve(
      __dirname,
      "../../../../var/reports/real-conversations-v1/matrix40-v1-final",
    ),
);
test.skip(
  process.env.MAB_ENABLE_PRIVATE_REPLAY !== "1" || !fs.existsSync(path.join(source, "manifest.json")),
  "A reconciliação local exige MAB_ENABLE_PRIVATE_REPLAY=1 e a coleta privada congelada.",
);
test.use({ video: "on", viewport: { width: 1440, height: 1000 } });
test.beforeEach(() => {
  fs.mkdirSync(evidence, { recursive: true });
});
test.afterEach(async ({ page }, info) => {
  await page.screenshot({
    path: path.join(evidence, `${info.title}.png`),
    fullPage: true,
  });
  const video = page.video();
  await page.context().close();
  if (video) await video.saveAs(path.join(evidence, `${info.title}.webm`));
});

test("UI05-replay-600-navegacao-completa", async ({ page }) => {
  test.setTimeout(120000);
  const methods: string[] = [],
    errors: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/")) methods.push(r.method());
  });
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/research");
  await expect(page.getByText("356 / 600", { exact: true })).toBeVisible();
  await page.screenshot({
    path: path.join(evidence, "UI05-visao-geral.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "600 execuções", exact: true })
    .click();
  await expect(page.getByTestId("filtered-count")).toContainText("600 de 600");
  await page.getByRole("button", { name: "Próxima", exact: true }).click();
  await expect(page.getByText("Página 2 de 20")).toBeVisible();
  await page.getByLabel("Buscar cenário, texto ou ID").fill("R-stock-03");
  await expect(page.getByTestId("filtered-count")).toContainText("15 de 600");
  await page
    .getByRole("button", {
      name: "Abrir R-stock-03 Centralizada repetição 0",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("heading", { name: "Resposta final coletada" }),
  ).toBeVisible();
  await page.screenshot({
    path: path.join(evidence, "UI05-conversa.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Agentes e ferramentas", exact: true })
    .click();
  await page
    .getByRole("group")
    .filter({ hasText: "stock_lookup" })
    .first()
    .locator("summary")
    .click();
  await page.screenshot({
    path: path.join(evidence, "UI05-ferramentas.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Comparar arquiteturas", exact: true })
    .click();
  await expect(
    page.getByText(/Hashes da entrada inicial idênticos/),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Inspecionar Workflow", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: path.join(evidence, "UI05-comparacao.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Gabarito e avaliação", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Critérios do juiz principal" }),
  ).toBeVisible();
  await page.screenshot({
    path: path.join(evidence, "UI05-avaliacao.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Eventos", exact: true }).click();
  await expect(page.getByText(/eventos registrados/)).toBeVisible();
  await page
    .getByRole("button", { name: "Próximo registro", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: /R-stock-03 · .* · repetição/ }).first(),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Resposta final coletada" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Fechar", exact: true }).click();
  await page
    .getByRole("button", { name: "Limpar filtros", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "Julgamento", exact: true })
    .selectOption("invalid");
  await expect(page.getByTestId("filtered-count")).toContainText("1 de 600");
  await page.getByRole("button", { name: /Abrir R-faq-05/ }).click();
  await page
    .getByRole("button", { name: "Gabarito e avaliação", exact: true })
    .click();
  await expect(
    page.getByText(/Julgamento inválido preservado como ausente/),
  ).toBeVisible();
  await page.screenshot({
    path: path.join(evidence, "UI05-juiz-invalido.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "600 execuções", exact: true })
    .click();
  await page
    .getByLabel("Buscar cenário, texto ou ID")
    .fill("nao-existe-essa-entrada");
  await expect(page.getByText(/Nenhum registro corresponde/)).toBeVisible();
  await page
    .getByRole("button", { name: "Limpar filtros", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "Arquitetura", exact: true })
    .selectOption("decentralized_swarm");
  await expect(page.getByTestId("filtered-count")).toContainText("200 de 600");
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "CSV de métricas" }).click();
  const csvPath = await (await download).path();
  expect(fs.readFileSync(csvPath!, "utf8").split("\n")).toHaveLength(201);
  await page.getByRole("button", { name: "40 cenários", exact: true }).click();
  await expect(page.getByRole("button", { name: /^Explorar R-/ })).toHaveCount(
    40,
  );
  await page.screenshot({
    path: path.join(evidence, "UI05-cenarios.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Qualidade e consumo", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Distribuição das notas de qualidade" }),
  ).toBeVisible();
  await page.screenshot({
    path: path.join(evidence, "UI05-qualidade.png"),
    fullPage: true,
  });
  const axe = await new AxeBuilder({ page }).analyze();
  fs.writeFileSync(
    path.join(evidence, "axe-research.json"),
    JSON.stringify(axe, null, 2),
  );
  expect(axe.violations).toEqual([]);
  expect(errors).toEqual([]);
  expect(new Set(methods)).toEqual(new Set(["GET"]));
});

test("UI06-replay-mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/research");
  await expect(page.getByText("356 / 600", { exact: true })).toBeVisible();
  await page.screenshot({
    path: path.join(evidence, "UI06-visao-geral-mobile.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "600 execuções", exact: true })
    .click();
  await page.getByLabel("Buscar cenário, texto ou ID").fill("R-media-02");
  await expect(page.getByTestId("filtered-count")).toContainText("15 de 600");
  await page
    .getByRole("button", {
      name: "Abrir R-media-02 Centralizada repetição 0",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("heading", { name: "Resposta final coletada" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const axe = await new AxeBuilder({ page }).analyze();
  fs.writeFileSync(
    path.join(evidence, "axe-mobile.json"),
    JSON.stringify(axe, null, 2),
  );
  expect(axe.violations).toEqual([]);
});

test("UI10-replay-falha-e-recuperacao", async ({ page }) => {
  let fail = true;
  await page.route("**/api/research", async (route) => {
    if (fail)
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: '{"error":"Lote indisponível na auditoria"}',
      });
    else await route.fallback();
  });
  await page.goto("/research");
  await expect(
    page.getByTestId("research-workspace").getByRole("alert"),
  ).toContainText("Lote indisponível");
  fail = false;
  await page.getByRole("button", { name: "Tentar novamente" }).click();
  await expect(page.getByText("356 / 600", { exact: true })).toBeVisible();
  await page.goto("/research?run=invalid-run");
  await expect(
    page.getByTestId("research-workspace").getByRole("alert"),
  ).toContainText("Execução não encontrada");
});

test("reconciliacao-600-detalhes-em-memoria", async ({ request }) => {
  test.setTimeout(120000);
  const response = await request.get("/api/research");
  expect(response.ok()).toBe(true);
  const data = await response.json();
  expect(data.rows).toHaveLength(600);
  expect(data.storage).toBe("memory");
  let valid = 0,
    success = 0,
    tokens = 0,
    requests = 0;
  const originals = new Map(
    fs
      .readFileSync(path.join(source, "aggregated-evaluations.jsonl"), "utf8")
      .trim()
      .split("\n")
      .map((line) => {
        const row = JSON.parse(line);
        return [row.run_id, row];
      }),
  );
  const hashes = new Map<string, Set<string>>();
  for (let offset = 0; offset < 600; offset += 20) {
    const results = await Promise.all(
      data.rows
        .slice(offset, offset + 20)
        .map(async (row: { run_id: string }) => {
          const r = await request.get(`/api/research?run=${row.run_id}`);
          expect(r.ok()).toBe(true);
          return r.json();
        }),
    );
    results.forEach((d) => {
      const original = originals.get(d.record.run_id)!;
      for (const key of [
        "task_success",
        "content_success",
        "procedure_compliance",
        "procedure_applicable",
        "end_to_end_latency_ms",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "model_requests",
      ])
        expect(d.record[key]).toEqual(original[key]);
      expect(d.evaluation?.quality ?? null).toEqual(
        original.evaluation?.quality ?? null,
      );
      for (const [file, hash] of Object.entries(d.source_hashes))
        expect(
          createHash("sha256")
            .update(fs.readFileSync(path.join(source, d.record.unit_id, file)))
            .digest("hex"),
        ).toEqual(hash);
      const group = `${d.record.scenario_id}-${d.record.repetition}`;
      if (!hashes.has(group)) hashes.set(group, new Set());
      expect(d.initial_input_sha256).not.toBeNull();
      hashes.get(group)!.add(d.initial_input_sha256);
      expect(d.input).toBeTruthy();
      expect(d.events.length).toBeGreaterThan(0);
      expect(Object.keys(d.source_hashes)).toHaveLength(3);
      expect(d.gold).not.toBeNull();
      valid += d.evaluation ? 1 : 0;
      success += d.record.task_success ? 1 : 0;
      tokens += d.record.total_tokens;
      requests += d.record.model_requests;
    });
  }
  expect(valid).toBe(599);
  expect(success).toBe(356);
  expect(tokens).toBe(3176535);
  expect(requests).toBe(2123);
  expect(hashes.size).toBe(200);
  for (const group of hashes.values()) expect(group.size).toBe(1);
  expect((await request.post("/api/research", { data: {} })).status()).toBe(
    405,
  );
  fs.writeFileSync(
    path.join(evidence, "reconciliacao-600.json"),
    JSON.stringify(
      {
        details: 600,
        valid_judge: valid,
        task_success: success,
        task_failed: 600 - success,
        generation_tokens: tokens,
        model_requests: requests,
        mutation_status: 405,
        storage: "memory",
      },
      null,
      2,
    ),
  );
});
