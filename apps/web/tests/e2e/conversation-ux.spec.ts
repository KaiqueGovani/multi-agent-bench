import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

const id = mockIds.centralizedConversation;
const title = "Disponibilidade e entrega de medicamentos";
const architectures = ["centralized_orchestration", "structured_workflow", "decentralized_swarm"];
const runs = [0, 1].flatMap((turn) => architectures.map((architectureKey, index) => ({
  id: `turn-${turn + 1}-run-${index + 1}`,
  conversationId: id,
  messageId: `message-${turn + 1}`,
  correlationId: `correlation-${turn + 1}`,
  status: "completed",
  totalDurationMs: 1200 + index * 300,
  createdAt: `2026-11-17T12:0${turn}:00.000Z`,
  updatedAt: `2026-11-17T12:0${turn}:02.000Z`,
  experiment: { architectureKey, scenarioId: "stock_inquiry" },
  summary: { inputTokens: 1200, outputTokens: 100, totalTokens: 1300, toolCallCount: 2 },
})));
const messages = [0, 1].flatMap((turn) => [
  { id: `message-${turn + 1}`, conversationId: id, direction: "inbound", contentText: turn ? "Vocês entregam o medicamento?" : "Tem dipirona disponível?", status: "completed", correlationId: `correlation-${turn + 1}`, createdAtServer: `2026-11-17T12:0${turn}:00.000Z`, metadata: {} },
  ...architectures.map((architectureMode, index) => ({
    id: `reply-${turn + 1}-${index + 1}`, conversationId: id, direction: "outbound", contentText: `Resposta da mensagem ${turn + 1}, arquitetura ${index + 1}.`, status: "completed", correlationId: `correlation-${turn + 1}`, createdAtServer: `2026-11-17T12:0${turn}:02.000Z`, metadata: { runtimeRunId: `turn-${turn + 1}-run-${index + 1}`, architectureMode },
  })),
]);

async function prepare(page: Page) {
  await installMockEventSource(page);
  await mockFrontendApi(page);
  let deleted = false;
  let failDelete = false;
  let deleteCount = 0;
  const summary = { conversationId: id, title, status: "completed", channel: "web_chat", updatedAt: runs[3].createdAt, lastMessage: messages[4].contentText, architectureMode: "all_architectures", messageCount: messages.length, eventCount: 6, reviewPending: false };
  await page.route("**/conversations", (route) => route.fulfill({ json: { conversations: deleted ? [] : [summary] } }));
  await page.route(`**/conversations/${id}`, (route) => {
    if (route.request().method() === "DELETE") {
      deleteCount += 1;
      if (failDelete) return route.fulfill({ status: 503, json: { detail: "Falha temporária ao excluir." } });
      deleted = true;
      return route.fulfill({ status: 204 });
    }
    return route.fulfill({ json: {
      conversation: { id, title, channel: "web_chat", status: "completed", createdAt: runs[0].createdAt, updatedAt: runs[3].createdAt, metadata: { architectureMode: "all_architectures" } },
      messages, runs, attachments: [], events: [], reviewTasks: [],
    } });
  });
  await page.route("**/runs/*/execution", (route) => {
    const run = runs.find((candidate) => candidate.id === new URL(route.request().url()).pathname.split("/")[2]);
    if (!run) return route.fulfill({ status: 404 });
    const roles = run.experiment.architectureKey === "centralized_orchestration" ? ["supervisor", "stock"] : run.experiment.architectureKey === "structured_workflow" ? ["router", "stock", "synthesizer"] : ["coordinator", "stock", "synthesizer"];
    const events = roles.flatMap((actorName, index) => ["started", "completed"].map((eventName, offset) => ({
      id: `${run.id}-event-${index}-${offset}`, runId: run.id, conversationId: id, messageId: run.messageId, correlationId: run.correlationId,
      eventFamily: "agent", eventName, status: eventName === "started" ? "running" : "completed", actorName,
      sequenceNo: index * 2 + offset + 1, createdAt: run.createdAt,
      payload: { agentInvocationId: `${run.id}-${actorName}`, ...(index > 0 && roles[0] === "supervisor" ? { parentAgentInvocationId: `${run.id}-supervisor` } : {}) },
    })));
    return route.fulfill({ json: { run, projection: { architectureMode: run.experiment.architectureKey, runStatus: run.status, architectureView: { actors: {}, stages: [], handoffs: [] }, metrics: { eventCount: events.length, toolCallCount: 2 }, state: {} }, executionEvents: events } });
  });
  await page.goto(`/?conversationId=${id}`);
  await expect(page.getByTestId("run-selector")).toBeVisible();
  return { setDeleteFailure(value: boolean) { failDelete = value; }, deleteCount: () => deleteCount };
}

test("keeps the selected historical run in sync across chat and overview", async ({ page }) => {
  await prepare(page);
  const selector = page.getByLabel("Execução", { exact: true });
  await expect(selector).toHaveValue("turn-2-run-1");
  await selector.selectOption("turn-1-run-2");
  await page.getByTestId("flow-toggle").click();
  await expect(page.getByTestId("runtime-visual-workflow")).toBeVisible();
  await expect(page.getByTestId("run-selector")).toContainText("Tem dipirona disponível?");
  await page.getByRole("button", { name: "Visão Geral", exact: true }).click();
  await expect(selector).toHaveValue("turn-1-run-2");
  await expect(page.getByTestId("overview-run-turn-1-run-1")).toBeVisible();
  await expect(page.getByTestId("overview-run-turn-1-run-2")).toHaveAttribute("data-selected", "true");
  await expect(page.getByTestId("overview-run-turn-2-run-1")).toHaveCount(0);
  await page.getByRole("button", { name: "Mais recente", exact: true }).click();
  await expect(selector).toHaveValue("turn-2-run-1");
  await expect(page.getByTestId("overview-run-turn-2-run-1")).toBeVisible();
  await expect(page.getByTestId("overview-run-turn-1-run-1")).toHaveCount(0);
});

test("shows generated titles and deletes the full selected conversation after confirmation", async ({ page }) => {
  const state = await prepare(page);
  await expect(page.getByText(title, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Expandir histórico", exact: true }).click();
  await expect(page.getByTestId(`conversation-row-${id}`)).toContainText(title);
  await page.getByRole("button", { name: "Excluir conversa", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Excluir conversa?" });
  await expect(dialog).toContainText("todas as execuções");
  await dialog.getByRole("button", { name: "Cancelar", exact: true }).click();
  expect(state.deleteCount()).toBe(0);
  await page.getByRole("button", { name: "Excluir conversa", exact: true }).click();
  state.setDeleteFailure(true);
  await dialog.getByRole("button", { name: "Excluir definitivamente", exact: true }).click();
  await expect(dialog.getByRole("alert")).toContainText("Falha temporária");
  await expect(page.getByTestId("run-selector")).toBeAttached();
  state.setDeleteFailure(false);
  await dialog.getByRole("button", { name: "Excluir definitivamente", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByText("Nenhuma conversa ativa")).toBeVisible();
  await expect(page.getByTestId(`conversation-row-${id}`)).toHaveCount(0);
  await expect(page.getByTestId("run-selector")).toHaveCount(0);
  expect(state.deleteCount()).toBe(2);
});

test("a late failed send cannot restore a deleted conversation or clear the new draft", async ({ page }) => {
  await prepare(page);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/messages", async (route) => {
    await gate;
    await route.fulfill({ status: 503, json: { detail: "Falha de uma conversa já excluída." } });
  });
  await page.getByTestId("message-composer-input").fill("Mensagem em envio");
  const request = page.waitForRequest((item) => item.method() === "POST" && item.url().endsWith("/messages"));
  await page.getByRole("button", { name: "Enviar mensagem", exact: true }).click();
  await request;
  await page.getByRole("button", { name: "Excluir conversa", exact: true }).click();
  await page.getByRole("button", { name: "Excluir definitivamente", exact: true }).click();
  await expect(page.getByText("Nenhuma conversa ativa")).toBeVisible();
  await page.getByTestId("message-composer-input").fill("Novo rascunho");
  release();
  await expect(page.getByTestId("message-composer-input")).toHaveValue("Novo rascunho");
  await expect(page.getByText("Falha de uma conversa já excluída.", { exact: false })).toHaveCount(0);
  await expect(page.getByTestId("run-selector")).toHaveCount(0);
});

for (const width of [1440, 1024, 768, 390]) {
  test(`overview keeps every card inside the viewport at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 950 });
    await prepare(page);
    await page.getByRole("button", { name: "Visão Geral", exact: true }).click();
    const overview = page.getByTestId("conversation-overview");
    await expect(page.getByTestId("overview-run-turn-2-run-1")).toBeVisible();
    await expect.poll(() => overview.evaluate((el) => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    for (const card of await overview.locator('[data-testid^="overview-run-"]').all()) {
      const bounds = await card.boundingBox();
      expect(bounds!.x).toBeGreaterThanOrEqual(0);
      expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width);
      expect(await card.evaluate((el) => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
      for (const metric of await card.locator("dl > div").all()) {
        expect(await metric.evaluate((el) => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
      }
    }
    if (width === 1440 || width === 390) {
      const directory = path.resolve(__dirname, "../../../../research-data/local/ui-refresh");
      fs.mkdirSync(directory, { recursive: true });
      await page.screenshot({ path: path.join(directory, `overview-${width}.png`), fullPage: true });
      if (width === 1440) {
        await page.getByRole("button", { name: "Conversa", exact: true }).click();
        await page.getByTestId("flow-toggle").click();
        await page.screenshot({ path: path.join(directory, "chat-run-selector-desktop.png"), fullPage: true });
      }
    }
  });
}
