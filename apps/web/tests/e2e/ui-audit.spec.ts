import { expect, test } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";
import AxeBuilder from "@axe-core/playwright";
import {
  installMockEventSource,
  mockFrontendApi,
  mockIds,
} from "./support/mock-runtime-fixtures";

const before = process.env.MAB_AUDIT_PHASE === "antes";
const beforeA11y = process.env.MAB_AUDIT_A11Y_BASELINE === "1";
const evidence = path.resolve(
  __dirname,
  "../../../../research-data/local/auditoria-ui-20261012",
  before || beforeA11y ? "antes" : "depois",
);
test.use({ video: "on", viewport: { width: 1440, height: 1000 } });
test.afterEach(async ({ page }, info) => {
  fs.mkdirSync(evidence, { recursive: true });
  await page.screenshot({
    path: path.join(evidence, `${info.title}.png`),
    fullPage: true,
  });
  const video = page.video();
  await page.context().close();
  if (video) await video.saveAs(path.join(evidence, `${info.title}.webm`));
});
test.beforeEach(async ({ page }) => {
  await installMockEventSource(page);
  await mockFrontendApi(page);
});

test("UI01-envio-falho-preserva-rascunho", async ({ page }) => {
  await page.route("**/messages", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Falha simulada na auditoria" }),
    }),
  );
  await page.goto(`/?conversationId=${mockIds.centralizedConversation}`);
  const input = page.getByTestId("message-composer-input");
  await input.fill("Mensagem que não pode ser perdida");
  await page.locator("input[type=file]").setInputFiles({ name: "auditoria.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4\nAuditoria local") });
  await page
    .getByRole("button", {
      name: before ? "Enviar" : "Enviar mensagem",
      exact: true,
    })
    .click();
  await expect(page.getByText(/Falha simulada na auditoria/)).toBeVisible();
  await expect(input).toHaveValue(
    before ? "" : "Mensagem que não pode ser perdida",
  );
  await expect(page.getByText("auditoria.pdf", { exact: true })).toHaveCount(before ? 0 : 1);
});

test("UI02-modal-foco-e-teclado", async ({ page }) => {
  await page.goto(`/?conversationId=${mockIds.centralizedConversation}`);
  const trigger = page.getByRole("button", { name: "Inspeção", exact: true });
  await expect(trigger).toBeEnabled();
  await trigger.focus();
  await trigger.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  const inside = await dialog.evaluate((el) =>
    el.contains(document.activeElement),
  );
  expect(inside).toBe(!before);
  if (!before) {
    await dialog.getByRole("button", { name: "Fechar inspeção" }).focus();
    await page.keyboard.press("Shift+Tab");
    expect(
      await dialog.evaluate((el) => el.contains(document.activeElement)),
    ).toBe(true);
    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
    await expect(trigger).toBeFocused();
    await trigger.click();
  }
});

test("UI03-chat-mobile-controles", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/?conversationId=${mockIds.centralizedConversation}`);
  await expect(page.getByTestId("message-composer-input")).toBeVisible();
  if (!before) {
    await expect(
      page.getByRole("button", { name: "Enviar mensagem", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Anexar arquivos", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Inspeção", exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
});

test("UI04-dashboard-falha-sem-contexto-antigo", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.getByText("Monitor técnico da conversa")).toBeVisible();
  await expect(
    page.getByText("conversa 11111111", { exact: true }),
  ).toBeVisible();
  await page.route(
    `**/conversations/${mockIds.workflowConversation}`,
    (route) =>
      route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Conversa indisponível" }),
      }),
  );
  await page
    .getByTestId(`dashboard-conversation-${mockIds.workflowConversation}`)
    .getByRole("button", { name: "Inspecionar" })
    .click();
  await expect(page.getByText(/Conversa indisponível/)).toBeVisible();
  await expect(
    page.getByText("conversa 11111111", { exact: true }),
  ).toHaveCount(before ? 1 : 0);
});

test("UI07-fluxo-restaurado", async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem("chat-flow-open", "true"),
  );
  await page.goto("/");
  await expect(page.getByTestId("flow-toggle")).toHaveAttribute(
    "aria-pressed",
    before ? "false" : "true",
  );
});

test("UI08-modo-de-execucao-explicito", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.locator("button[aria-label*='Modo de execução']"),
  ).toContainText(before ? "LLM off" : "Real indisponível");
});

test("UI12-revisao-bloqueia-envio-duplicado", async ({ page }) => {
  let release!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  let requests = 0;
  await page.route("**/reviews/*/resolve", async route => { requests++; await pending; await route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"Revisão indisponível na auditoria"}' }); });
  await page.goto("/dashboard");
  const approve = page.getByRole("button", { name: "Aprovar", exact: true });
  await expect(approve).toBeVisible();
  await approve.click();
  await expect.poll(() => requests).toBe(1);
  if (before) await expect(approve).toBeEnabled(); else await expect(approve).toBeDisabled();
  await page.screenshot({ path: path.join(evidence, "UI12-revisao-em-andamento.png"), fullPage: true });
  release();
  await expect(page.getByText(/Revisão indisponível na auditoria/)).toBeVisible();
  await expect(approve).toBeEnabled();
});

test("UI11-acessibilidade-fluxos-originais", async ({ page }) => {
  test.skip(before, "Varredura automatizada adicionada na validação final.");
  const reports: Record<string, unknown> = {};
  await page.goto(`/?conversationId=${mockIds.centralizedConversation}`);
  await expect(page.getByTestId("message-list")).toContainText("dipirona");
  reports.chat = await new AxeBuilder({ page }).analyze();
  await page.screenshot({
    path: path.join(evidence, "UI11-chat.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Visão Geral", exact: true }).click();
  reports.overview = await new AxeBuilder({ page }).analyze();
  await page.screenshot({
    path: path.join(evidence, "UI11-visao-geral.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Atividade", exact: true }).click();
  reports.events = await new AxeBuilder({ page }).analyze();
  await page.screenshot({
    path: path.join(evidence, "UI11-atividade.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Inspeção", exact: true }).click();
  reports.inspector = await new AxeBuilder({ page }).analyze();
  await page.screenshot({
    path: path.join(evidence, "UI11-inspecao.png"),
    fullPage: true,
  });
  await page.keyboard.press("Escape");
  await page.goto("/dashboard");
  await expect(page.getByText("Monitor técnico da conversa")).toBeVisible();
  await expect(
    page.getByText("conversa 11111111", { exact: true }),
  ).toBeVisible();
  await page.waitForTimeout(1200); // Allow the existing entrance animation to settle before contrast measurement.
  reports.dashboard = await new AxeBuilder({ page }).analyze();
  fs.writeFileSync(
    path.join(evidence, "axe-original-ui.json"),
    JSON.stringify(reports, null, 2),
  );
  if (!beforeA11y)
    for (const report of Object.values(reports))
      expect((report as { violations: unknown[] }).violations).toEqual([]);
});

test("UI13-responsividade-chat-dashboard", async ({ page }) => {
  test.skip(before, "Validação adicional após as correções.");
  for (const width of [320, 768, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(`/?conversationId=${mockIds.centralizedConversation}`);
    await expect(page.getByTestId("message-composer-input")).toBeVisible();
    for (const name of ["Conversa", "Visão Geral", "Atividade"]) {
      const box = await page.getByRole("button", { name, exact: true }).boundingBox();
      expect(box!.x).toBeGreaterThanOrEqual(0); expect(box!.x + box!.width).toBeLessThanOrEqual(width);
    }
    await page.screenshot({ path: path.join(evidence, `UI13-chat-${width}.png`), fullPage: true });
    await page.goto("/dashboard");
    await expect(page.getByText("Monitor técnico da conversa")).toBeVisible();
    const overflow = await page.evaluate(() => Array.from(document.querySelectorAll("body *")).map(el => { const r = el.getBoundingClientRect(); return { tag: el.tagName, classes: el.className, width: r.width, right: r.right }; }).filter(r => r.right > innerWidth + 1 && r.width > 0));
    fs.writeFileSync(path.join(evidence, `UI13-overflow-${width}.json`), JSON.stringify(overflow, null, 2));
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: path.join(evidence, `UI13-dashboard-${width}.png`), fullPage: true });
  }
});
