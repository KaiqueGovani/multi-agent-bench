import { expect, test } from "@playwright/test";
import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

test("imported attendant history stays visible across architectures and only model suggestions can be copied", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await installMockEventSource(page);
  await mockFrontendApi(page);
  const now = new Date().toISOString();
  const conversationId = mockIds.centralizedConversation;
  const architectures = ["centralized_orchestration", "structured_workflow"];
  const runs = architectures.map((architectureKey, i) => ({
    id: i ? mockIds.workflowRun : mockIds.centralizedRun, conversationId,
    messageId: "target", correlationId: "test", status: "completed", createdAt: now, updatedAt: now,
    humanReviewRequired: false, experiment: { architectureKey }, summary: {},
  }));
  const base = { conversationId, correlationId: "test", createdAtServer: now, status: "completed" };
  const messages = [
    { ...base, id: "history", direction: "outbound", contentText: "Olá, como posso ajudar?", metadata: { importedHistory: true, sourceRole: "attendant" } },
    { ...base, id: "target", direction: "inbound", contentText: "Vocês têm dipirona?", metadata: { importedHistory: true, sourceRole: "customer" } },
    ...runs.map((run, i) => ({ ...base, id: `response-${i}`, direction: "outbound", contentText: `Sugestão ${i + 1}`, metadata: { runtimeRunId: run.id, architectureMode: architectures[i] } })),
  ];
  await page.route(`**/conversations/${conversationId}`, async route => route.fulfill({json: {
    conversation: { id: conversationId, channel: "whatsapp", status: "active", createdAt: now, updatedAt: now, metadata: { source: "whatsapp_web", architectureMode: "all_architectures", runtimeMode: "mock", comparisonProtocol: null } },
    messages, runs, attachments: [], events: [], reviewTasks: [],
  }}));
  await page.route("**/health", route => route.fulfill({ json: { status: "ok", runtime: { ready: true, reachable: true, mode: "real" } } }));
  await page.goto(`/?conversationId=${conversationId}`);
  await expect(page.getByTestId("whatsapp-import-banner")).toBeVisible();
  const list = page.getByTestId("message-list");
  await expect(list.getByText("Atendente · WhatsApp")).toBeVisible();
  await expect(list.getByText("Olá, como posso ajudar?")).toBeVisible();
  await expect(list.getByText("Sugestão 1", { exact: true })).toBeVisible();
  await expect(list.getByRole("button", { name: "Copiar resposta", exact: true })).toHaveCount(1);
  await list.getByRole("button", { name: "Copiar resposta", exact: true }).click();
  await expect(list.getByText("Copiada", { exact: true })).toBeVisible();
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe("Sugestão 1");
  await page.getByRole("button", { name: /Workflow.*run/ }).click();
  await expect(list.getByText("Olá, como posso ajudar?")).toBeVisible();
  await expect(list.getByText("Sugestão 2", { exact: true })).toBeVisible();
  await expect(list.getByText("Sugestão 1", { exact: true })).toHaveCount(0);
  // The API selects the application protocol for a real WhatsApp turn.
  await page.getByRole("button", { name: "Modo de execução: Simulado", exact: true }).click();
  await page.getByTestId("message-composer-input").fill("E qual é o horário?");
  const sent = page.waitForRequest(request => request.method() === "POST" && request.url().endsWith("/messages"));
  await page.getByRole("button", { name: "Enviar mensagem", exact: true }).click();
  const body = (await sent).postData() || "";
  expect(body).toContain('"runtimeMode":"real"');
  expect(body).not.toContain('"comparisonProtocol"');
});
