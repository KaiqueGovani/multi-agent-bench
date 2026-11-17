import { expect, test, type Page } from "@playwright/test";

import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

const testKey = "provider-ui-test-credential";
const bedrockModel = "us.anthropic.claude-haiku-4-5-20251001-v1:0";
const anthropicModel = "claude-haiku-4-5-20251001";

function runtimeStatus(ready: boolean) {
  return {
    mode: "real",
    runtimeUrl: "http://127.0.0.1:8010",
    reachable: true,
    ready,
    llm: {
      provider: "bedrock",
      models: { bedrock: bedrockModel, anthropic: anthropicModel },
      credentialsConfigured: { bedrock: ready, anthropic: false },
      enabled: true,
      tokenConfigured: ready,
      sdkAvailable: true,
      ready,
      modelId: bedrockModel,
      region: "us-east-1",
    },
    error: ready ? null : "Agent runtime is reachable, but live LLM is not ready.",
  };
}

async function prepareChat(page: Page) {
  await installMockEventSource(page);
  await mockFrontendApi(page);
  await page.route("**/health", (route) => route.fulfill({
    json: {
      status: "ok",
      service: "test-api",
      version: "test",
      environment: "test",
      runtime: runtimeStatus(false),
    },
  }));
  await page.route("**/settings/llm", (route) => route.fulfill({ json: runtimeStatus(false) }));
  await page.route("**/settings/llm/models", (route) => route.fulfill({ status: 500, json: { detail: "Unexpected model request in test" } }));
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Modo de execução: Real indisponível" })).toBeVisible();
}

test("applies a replacement key immediately and keeps it out of browser storage", async ({ page }) => {
  await prepareChat(page);
  const requests: Array<{ method: string; body: unknown }> = [];
  await page.route("**/settings/llm", async (route) => {
    if (route.request().method() === "GET") return route.fulfill({ json: runtimeStatus(false) });
    requests.push({ method: route.request().method(), body: route.request().postDataJSON() });
    await route.fulfill({ json: runtimeStatus(true) });
  });

  await page.getByRole("button", { name: "Configurar provedor de IA" }).click();
  const dialog = page.getByRole("dialog", { name: "Provedor de IA" });
  const input = dialog.getByLabel("Nova chave de API", { exact: true });
  await expect(input).toHaveAttribute("type", "password");
  await expect(dialog.getByRole("button", { name: "Aplicar configuração", exact: true })).toBeDisabled();
  await expect(input).toBeEnabled();
  await input.fill(`  ${testKey}  `);
  await dialog.getByRole("button", { name: "Mostrar chave", exact: true }).click();
  await expect(input).toHaveAttribute("type", "text");
  await dialog.getByRole("button", { name: "Ocultar chave", exact: true }).click();
  await expect(input).toHaveAttribute("type", "password");
  await dialog.getByRole("button", { name: "Aplicar configuração", exact: true }).click();

  await expect(dialog.getByRole("status")).toContainText("Configuração atualizada. As próximas execuções usarão o provedor e o modelo selecionados.");
  await expect(input).toHaveValue("");
  await expect(page.getByRole("button", { name: "Modo de execução: Real disponível", includeHidden: true })).toBeAttached();
  expect(requests).toEqual([{ method: "PUT", body: { provider: "bedrock", modelId: bedrockModel, apiKey: testKey } }]);
  const storedValues = await page.evaluate(() => [
    ...Object.values(localStorage),
    ...Object.values(sessionStorage),
  ]);
  expect(storedValues.join(" ")).not.toContain(testKey);

  // A second rotation works in the same running page without a reload.
  await expect(input).toBeEnabled();
  await input.fill(`${testKey}-replacement`);
  await dialog.getByRole("button", { name: "Aplicar configuração", exact: true }).click();
  await expect.poll(() => requests.length).toBe(2);
  await expect(input).toHaveValue("");
  expect(requests[1]).toEqual({ method: "PUT", body: { provider: "bedrock", modelId: bedrockModel, apiKey: `${testKey}-replacement` } });
});

test("shows a save failure and allows retry without changing runtime readiness", async ({ page }) => {
  await prepareChat(page);
  let attempts = 0;
  await page.route("**/settings/llm", async (route) => {
    if (route.request().method() === "GET") return route.fulfill({ json: runtimeStatus(false) });
    attempts += 1;
    await route.fulfill(attempts === 1
      ? { status: 503, json: { detail: "O runtime está indisponível. Tente novamente." } }
      : { json: runtimeStatus(true) });
  });
  await page.getByRole("button", { name: "Configurar provedor de IA" }).click();
  const dialog = page.getByRole("dialog", { name: "Provedor de IA" });
  const input = dialog.getByLabel("Nova chave de API", { exact: true });
  await expect(input).toBeEnabled();
  await input.fill(testKey);
  await dialog.getByRole("button", { name: "Aplicar configuração", exact: true }).click();
  await expect(dialog.getByRole("alert")).toContainText("O runtime está indisponível. Tente novamente.");
  await expect(dialog.getByRole("button", { name: "Aplicar configuração", exact: true })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Modo de execução: Real indisponível", includeHidden: true })).toBeAttached();
  await dialog.getByRole("button", { name: "Aplicar configuração", exact: true }).click();
  await expect(dialog.getByRole("status")).toContainText("Configuração atualizada.");
  await expect(input).toHaveValue("");
  expect(attempts).toBe(2);
});

test("keeps mobile settings modal and clears an abandoned key", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await prepareChat(page);
  await page.goto(`/?conversationId=${mockIds.workflowConversation}`);
  await expect(page.getByTestId("review-badge-link")).toBeVisible();
  const trigger = page.getByRole("button", { name: "Configurar provedor de IA" });
  await trigger.click();
  const dialog = page.getByRole("dialog", { name: "Provedor de IA" });
  const input = dialog.getByLabel("Nova chave de API", { exact: true });
  await expect(input).toBeEnabled();
  await input.fill(testKey);
  await dialog.getByRole("button", { name: "Mostrar chave", exact: true }).click();
  for (let step = 0; step < 7; step += 1) {
    await page.keyboard.press("Tab");
    // Native dialogs may move focus to browser chrome between Tab cycles.
    // No control in the background page may receive focus.
    expect(await dialog.evaluate((element) => (
      document.activeElement === document.body || element.contains(document.activeElement)
    ))).toBe(true);
  }
  expect(await dialog.evaluate((element) => element.matches(":modal"))).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const bounds = await dialog.boundingBox();
  expect(bounds).not.toBeNull();
  expect(bounds!.x).toBeGreaterThanOrEqual(0);
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(390);
  const screenshotPath = test.info().outputPath("llm-settings-mobile.png");
  await page.screenshot({ fullPage: true, path: "/Users/kaiquemg/Repos/multi-agent-bench/research-data/local/llm-settings-mobile.png" });
  await page.screenshot({ fullPage: true, path: screenshotPath });
  await test.info().attach("llm-settings-mobile", {
    path: screenshotPath,
    contentType: "image/png",
  });
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
  await trigger.click();
  await expect(input).toHaveValue("");
  await expect(input).toHaveAttribute("type", "password");
  await dialog.getByRole("button", { name: "Fechar configurações de IA" }).click();
  await expect(dialog).not.toBeVisible();
});

test("prevents duplicate saves while a key update is pending", async ({ page }) => {
  await prepareChat(page);
  let requestCount = 0;
  let releaseUpdate!: () => void;
  const updateGate = new Promise<void>((resolve) => { releaseUpdate = resolve; });
  await page.route("**/settings/llm", async (route) => {
    if (route.request().method() === "GET") return route.fulfill({ json: runtimeStatus(false) });
    requestCount += 1;
    await updateGate;
    await route.fulfill({ json: runtimeStatus(true) });
  });
  await page.getByRole("button", { name: "Configurar provedor de IA" }).click();
  const dialog = page.getByRole("dialog", { name: "Provedor de IA" });
  const input = dialog.getByLabel("Nova chave de API", { exact: true });
  await expect(input).toBeEnabled();
  await input.fill(testKey);
  await dialog.getByRole("button", { name: "Aplicar configuração", exact: true }).click();
  await expect.poll(() => requestCount).toBe(1);
  await expect(input).toBeDisabled();
  await expect(dialog.locator("button[type=submit]")).toBeDisabled();
  await page.keyboard.press("Enter");
  expect(requestCount).toBe(1);
  releaseUpdate();
  await expect(dialog.getByRole("status")).toContainText("Configuração atualizada.");
  await expect(input).toHaveValue("");
});

test("switches to direct Anthropic with a custom model and reuses provider credentials", async ({ page }) => {
  await prepareChat(page);
  let active = "bedrock";
  const models = { bedrock: bedrockModel, anthropic: anthropicModel };
  const keys = { bedrock: true, anthropic: false };
  const updates: unknown[] = [];
  function status() {
    return { ...runtimeStatus(true), llm: {
      ...runtimeStatus(true).llm, provider: active, models: { ...models },
      credentialsConfigured: { ...keys }, modelId: models[active as keyof typeof models],
    } };
  }
  await page.route("**/settings/llm", async (route) => {
    if (route.request().method() === "PUT") {
      const body = route.request().postDataJSON();
      updates.push(body);
      active = body.provider;
      models[active as keyof typeof models] = body.modelId;
      keys[active as keyof typeof keys] = true;
    }
    await route.fulfill({ json: status() });
  });
  await page.getByRole("button", { name: "Configurar provedor de IA" }).click();
  const dialog = page.getByRole("dialog", { name: "Provedor de IA", exact: true });
  const provider = dialog.getByLabel("Provedor", { exact: true });
  const model = dialog.getByLabel("Modelo", { exact: true });
  const key = dialog.getByLabel("Nova chave de API", { exact: true });
  const apply = dialog.getByRole("button", { name: "Aplicar configuração", exact: true });
  await expect(provider).toBeEnabled();
  await provider.selectOption("anthropic");
  await expect(model).toHaveValue(anthropicModel);
  await expect(apply).toBeDisabled();
  await model.selectOption("__custom__");
  await dialog.getByLabel("Identificador do modelo", { exact: true }).fill("claude-custom-test");
  await key.fill(testKey);
  await apply.click();
  await expect(dialog.getByRole("status")).toContainText("Configuração atualizada.");
  await expect(key).toHaveValue("");
  await expect(page.getByRole("button", { name: "Configurar provedor de IA", includeHidden: true })).toHaveText("Anthropic");

  await provider.selectOption("bedrock");
  await expect(model).toHaveValue(bedrockModel);
  await expect(apply).toBeEnabled();
  await apply.click();
  await expect(dialog.getByRole("status")).toContainText("Configuração atualizada.");
  await provider.selectOption("anthropic");
  await expect(apply).toBeEnabled();
  await apply.click();
  await expect.poll(() => updates.length).toBe(3);
  expect(updates).toEqual([
    { provider: "anthropic", modelId: "claude-custom-test", apiKey: testKey },
    { provider: "bedrock", modelId: bedrockModel },
    { provider: "anthropic", modelId: "claude-custom-test" },
  ]);
});

test("loads the Anthropic model picker using a pasted key without applying settings", async ({ page }) => {
  await prepareChat(page);
  const modelRequests: unknown[] = [];
  const updates: unknown[] = [];
  await page.route("**/settings/llm", async (route) => {
    if (route.request().method() === "PUT") updates.push(route.request().postDataJSON());
    await route.fulfill({ json: runtimeStatus(false) });
  });
  await page.route("**/settings/llm/models", async (route) => {
    modelRequests.push(route.request().postDataJSON());
    await route.fulfill({ json: { provider: "anthropic", source: "provider", models: [
      { id: "claude-picker-test", name: "Claude Picker Test" },
      { id: "claude-second-test", name: "Claude Second Test" },
    ] } });
  });
  await page.getByRole("button", { name: "Configurar provedor de IA" }).click();
  const dialog = page.getByRole("dialog", { name: "Provedor de IA", exact: true });
  const provider = dialog.getByLabel("Provedor", { exact: true });
  await expect(provider).toBeEnabled();
  await provider.selectOption("anthropic");
  const load = dialog.getByRole("button", { name: "Carregar modelos", exact: true });
  await expect(load).toBeDisabled();
  await dialog.getByLabel("Nova chave de API", { exact: true }).fill(testKey);
  await expect(load).toBeEnabled();
  await load.click();
  const model = dialog.getByLabel("Modelo", { exact: true });
  await expect(model.getByRole("option", { name: "Claude Picker Test" })).toBeAttached();
  await expect(model).toHaveValue(anthropicModel);
  await model.selectOption("claude-picker-test");
  expect(modelRequests).toEqual([{ provider: "anthropic", apiKey: testKey }]);
  expect(updates).toHaveLength(0);
  await dialog.getByRole("button", { name: "Aplicar configuração", exact: true }).click();
  await expect.poll(() => updates.length).toBe(1);
  expect(updates[0]).toEqual({ provider: "anthropic", modelId: "claude-picker-test", apiKey: testKey });
});

test("ignores a delayed settings response after closing and reopening the dialog", async ({ page }) => {
  await prepareChat(page);
  let requests = 0;
  let release!: () => void;
  let completed!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const firstCompleted = new Promise<void>((resolve) => { completed = resolve; });
  await page.route("**/settings/llm", async (route) => {
    requests += 1;
    if (requests === 1) {
      await gate;
      await route.fulfill({ json: { ...runtimeStatus(true), llm: {
        ...runtimeStatus(true).llm, provider: "anthropic", modelId: anthropicModel,
      } } });
      completed();
    } else {
      await route.fulfill({ json: runtimeStatus(false) });
    }
  });
  const trigger = page.getByRole("button", { name: "Configurar provedor de IA" });
  await trigger.click();
  const dialog = page.getByRole("dialog", { name: "Provedor de IA", exact: true });
  const provider = dialog.getByLabel("Provedor", { exact: true });
  await expect(provider).toBeDisabled();
  await dialog.getByRole("button", { name: "Fechar configurações de IA" }).click();
  await expect(dialog).not.toBeVisible();
  await trigger.click();
  await expect(provider).toBeEnabled();
  await expect(provider).toHaveValue("bedrock");
  release();
  await firstCompleted;
  await expect(provider).toHaveValue("bedrock");
  await expect(dialog.getByLabel("Modelo", { exact: true })).toHaveValue(bedrockModel);
});
