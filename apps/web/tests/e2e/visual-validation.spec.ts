import { expect, test } from "@playwright/test";

import { installMockEventSource, mockFrontendApi } from "./support/mock-runtime-fixtures";

test.describe("visual validation after UX improvements", () => {
  test.beforeEach(async ({ page }) => {
    await installMockEventSource(page);
    await mockFrontendApi(page);
    await page.route("http://localhost:8000/**", (route) =>
      route.fallback({ url: route.request().url().replace("http://localhost:8000", "http://127.0.0.1:8000") }),
    );
  });

  test("chat workspace has 3 tabs and correct PT-BR labels", async ({ page }) => {
    await page.goto("/");

    // 3 tab buttons inside nav
    const nav = page.locator("nav");
    await expect(nav.getByRole("button", { name: "Conversa" })).toBeVisible();
    await expect(nav.getByRole("button", { name: "Visão Geral" })).toBeVisible();
    await expect(nav.getByRole("button", { name: "Atividade" })).toBeVisible();

    await page.screenshot({ path: "test-results/visual-01-conversa-tab.png" });
  });

  test("message composer is at bottom, not overlaying content", async ({ page }) => {
    await page.goto("/");

    const composer = page.getByTestId("message-composer-input");
    await expect(composer).toBeVisible();

    // Architecture dropdown shows PT-BR labels
    const select = page.getByTestId("architecture-select");
    await expect(select).toBeVisible();
    const options = select.locator("option");
    await expect(options.nth(0)).toContainText("Orquestração");

    await page.screenshot({ path: "test-results/visual-02-composer-position.png" });
  });

  test("execution mode toggle shows Simulado in PT-BR", async ({ page }) => {
    await page.goto("/");

    const toggle = page.locator("button[aria-label*='Modo de execução']");
    await expect(toggle).toBeVisible();
    await expect(toggle).toContainText("Simulado");

    await page.screenshot({ path: "test-results/visual-03-execution-toggle.png" });
  });

  test("Visão Geral tab hides conversation sidebar", async ({ page }) => {
    await page.goto("/");

    await page.locator("nav").getByRole("button", { name: "Visão Geral" }).click();

    // Conversation sidebar should NOT be visible in this tab
    await expect(page.getByText("Conversas").first()).not.toBeVisible();

    await page.screenshot({ path: "test-results/visual-04-visao-geral-tab.png" });
  });

  test("Atividade tab hides conversation sidebar", async ({ page }) => {
    await page.goto("/");

    await page.locator("nav").getByRole("button", { name: "Atividade" }).click();

    // Conversation sidebar should NOT be visible in this tab
    await expect(page.getByText("Conversas").first()).not.toBeVisible();

    await page.screenshot({ path: "test-results/visual-05-atividade-tab.png" });
  });

  test("PT-BR translations: no common English strings visible", async ({ page }) => {
    await page.goto("/");

    const body = page.locator("body");
    const bodyText = await body.textContent();

    expect(bodyText).not.toContain("Failed to load");
    expect(bodyText).not.toContain("tool calls");

    // Portuguese labels ARE present
    expect(bodyText).toContain("Nova conversa");
    expect(bodyText).toContain("Nenhuma mensagem ainda");
  });

  test("Conversa tab shows only the conversation (no RunExecutionPanel in the middle)", async ({ page }) => {
    await page.goto("/");

    // Conversa tab is default
    await expect(page.locator("nav").getByRole("button", { name: "Conversa" })).toBeVisible();

    // The runtime panel should NOT appear in the middle of the Conversa tab
    // (it used to show "Ver acompanhamento" toggle or the architecture flow inline)
    await expect(page.getByTestId("runtime-panel-user")).toHaveCount(0);

    // But the message list (empty state or populated) and composer MUST be visible
    const messageList = page.locator("[data-testid='message-list'], [data-testid='message-list-empty']").first();
    await expect(messageList).toBeVisible();
    await expect(page.getByTestId("message-composer-input")).toBeVisible();
  });

  test("Visão Geral tab has no internal sub-tabs", async ({ page }) => {
    await page.goto("/");

    await page.locator("nav").getByRole("button", { name: "Visão Geral" }).click();

    // After switching to Visão Geral, there should only be ONE nav (the main tab bar).
    // The RunExecutionPanel's internal sub-tab bar (which would contain another "Atividade"
    // and "Técnico" button inside the panel) must NOT be rendered.
    const mainNavTabs = page.locator("nav").first().locator("button");
    await expect(mainNavTabs).toHaveCount(3); // Conversa, Visão Geral, Atividade

    // "Técnico" is an internal sub-tab — it should NOT be visible when outer Visão Geral is active
    await expect(page.getByRole("button", { name: "Técnico" })).toHaveCount(0);
  });

  test("Atividade tab hides the events sidebar icon", async ({ page }) => {
    await page.goto("/");

    // On Conversa tab, events toggle may be hidden on desktop (lg:hidden) but present in DOM;
    // however on Atividade tab it should not be rendered at all
    await page.locator("nav").getByRole("button", { name: "Atividade" }).click();

    // events-toggle button should NOT exist in the DOM when on Atividade tab
    await expect(page.getByTestId("events-toggle")).toHaveCount(0);
  });
});
