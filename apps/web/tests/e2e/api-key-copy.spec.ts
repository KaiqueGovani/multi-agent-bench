import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

import { installMockEventSource, mockFrontendApi } from "./support/mock-runtime-fixtures";

async function prepareChat(page: Page, failures = 0) {
  await installMockEventSource(page);
  await mockFrontendApi(page);
  await page.addInitScript((failureCount) => {
    const state = { value: "", attempts: 0, failures: failureCount };
    Object.assign(window, { __extensionKeyClipboard: state });
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        async writeText(value: string) {
          state.attempts += 1;
          if (state.failures > 0) {
            state.failures -= 1;
            throw new DOMException("Clipboard permission denied", "NotAllowedError");
          }
          state.value = value;
        },
      },
    });
  }, failures);
  const apiRequest = page.waitForRequest((request) => request.method() === "GET" && request.url().endsWith("/conversations"));
  await page.goto("/");
  const configuredKey = (await apiRequest).headers()["x-api-key"] ?? "";
  // Keep the generated credential out of assertion output, including failures.
  expect(configuredKey.length >= 40 && configuredKey !== "poc-dev-key-2026").toBe(true);
  const copy = page.getByRole("button", { name: "Copiar chave da extensão", exact: true });
  await expect(copy).toBeEnabled();
  return { copy, configuredKey };
}

for (const width of [1440, 390]) {
  test(`copies the configured extension key without exposing it on the page at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const mutations: string[] = [];
    page.on("request", (request) => {
      if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) mutations.push(request.method());
    });
    const { copy, configuredKey } = await prepareChat(page);
    await expect(copy).toHaveAttribute("title", "Copiar chave da API do MAB para a extensão");
    await copy.click();
    await expect(page.getByRole("status").filter({ hasText: "Chave da extensão copiada." })).toHaveText("Chave da extensão copiada.");
    const checks = await page.evaluate((expected) => {
      const state = (window as unknown as { __extensionKeyClipboard: { value: string; attempts: number } }).__extensionKeyClipboard;
      return {
        matchesConfiguredKey: state.value === expected,
        attempts: state.attempts,
        exposedInPage: document.documentElement.outerHTML.includes(state.value),
      };
    }, configuredKey);
    expect(checks).toEqual({ matchesConfiguredKey: true, attempts: 1, exposedInPage: false });
    expect(mutations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const bounds = await copy.boundingBox();
    expect(bounds).not.toBeNull();
    expect(bounds!.x).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width);
    if (width === 390) {
      const directory = path.resolve(__dirname, "../../../../research-data/local/ui-polish");
      fs.mkdirSync(directory, { recursive: true });
      await page.screenshot({ path: path.join(directory, "header-key-copy-mobile.png"), fullPage: true });
    }
  });
}

test("a denied clipboard write shows an error and can be retried", async ({ page }) => {
  const { copy, configuredKey } = await prepareChat(page, 1);
  await copy.click();
  const error = page.getByRole("alert").filter({ hasText: /Não foi possível copiar/i });
  await expect(error).toBeVisible();
  await expect(copy).toBeEnabled();
  expect(await page.evaluate(() => (window as unknown as { __extensionKeyClipboard: { value: string } }).__extensionKeyClipboard.value.length)).toBe(0);
  await copy.click();
  await expect(page.getByRole("status").filter({ hasText: "Chave da extensão copiada." })).toHaveText("Chave da extensão copiada.");
  await expect(error).toHaveCount(0);
  expect(await page.evaluate((expected) => {
    const state = (window as unknown as { __extensionKeyClipboard: { value: string; attempts: number } }).__extensionKeyClipboard;
    return state.value === expected && state.attempts === 2;
  }, configuredKey)).toBe(true);
});
