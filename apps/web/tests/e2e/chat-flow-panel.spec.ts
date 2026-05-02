import { expect, test } from "@playwright/test";

import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

test.describe("chat flow panel (P5)", () => {
  test.beforeEach(async ({ page }) => {
    await installMockEventSource(page);
    await mockFrontendApi(page);
    await page.route("http://localhost:8000/**", (route) =>
      route.fallback({ url: route.request().url().replace("http://localhost:8000", "http://127.0.0.1:8000") }),
    );
  });

  test("flow toggle button is visible and panel opens with architecture flow", async ({ page }) => {
    await page.goto(`/?conversationId=${mockIds.centralizedConversation}`);

    // Toggle button exists
    const toggle = page.getByTestId("flow-toggle");
    await expect(toggle).toBeVisible();
    await expect(toggle).toHaveAttribute("aria-pressed", "false");

    // Panel not visible initially
    await expect(page.getByTestId("chat-flow-panel")).toHaveCount(0);

    // Click toggle
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-pressed", "true");

    // Panel is now visible with the centralized flow
    const panel = page.getByTestId("chat-flow-panel");
    await expect(panel).toBeVisible();
    await expect(page.getByTestId("runtime-visual-centralized")).toBeVisible();
  });

  test("flow panel shows placeholder when no run execution", async ({ page }) => {
    // Go to home without a conversation
    await page.goto("/");

    const toggle = page.getByTestId("flow-toggle");
    await toggle.click();

    const panel = page.getByTestId("chat-flow-panel");
    await expect(panel).toBeVisible();
    await expect(panel).toContainText("Envie uma mensagem para visualizar o fluxo");
  });

  test("flow panel closes when toggle is clicked again", async ({ page }) => {
    await page.goto(`/?conversationId=${mockIds.centralizedConversation}`);

    const toggle = page.getByTestId("flow-toggle");
    await toggle.click();
    await expect(page.getByTestId("chat-flow-panel")).toBeVisible();

    await toggle.click();
    await expect(page.getByTestId("chat-flow-panel")).toHaveCount(0);
  });

  test("flow panel persists open state via localStorage", async ({ page }) => {
    // Set localStorage before navigating
    await page.goto("/");
    await page.evaluate(() => localStorage.setItem("chat-flow-open", "true"));
    await page.goto(`/?conversationId=${mockIds.centralizedConversation}`);

    // Panel should auto-open
    await expect(page.getByTestId("chat-flow-panel")).toBeVisible();
    await expect(page.getByTestId("flow-toggle")).toHaveAttribute("aria-pressed", "true");
  });

  test("flow panel handles API error gracefully", async ({ page }) => {
    // Override the run execution endpoint to return 500
    await page.route("**/runs/*/execution", (route) =>
      route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "Internal error" }) }),
    );

    await page.goto(`/?conversationId=${mockIds.centralizedConversation}`);

    const toggle = page.getByTestId("flow-toggle");
    await toggle.click();

    // Panel shows placeholder (no projection available due to error)
    const panel = page.getByTestId("chat-flow-panel");
    await expect(panel).toBeVisible();
    await expect(panel).toContainText("Envie uma mensagem para visualizar o fluxo");
  });
});
