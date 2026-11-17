import { expect, test, type Page } from "@playwright/test";
import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

const conversationId = mockIds.centralizedConversation;
const inboundId = "review-input";
const taskId = "bound-review";
const timestamp = "2026-11-17T18:00:00Z";

function detail(status: "open" | "resolved" | "cancelled") {
  const message = (id: string, direction: string, contentText: string, correlationId: string, metadata = {}) => ({
    id, conversationId, direction, contentText, correlationId, metadata,
    status: "completed", createdAtServer: timestamp,
  });
  return {
    conversation: { id: conversationId, title: "Solicitação de dose e avaliação farmacêutica", channel: "web_chat", status: status === "open" ? "human_review_required" : "completed", createdAt: timestamp, updatedAt: timestamp, metadata: { architectureMode: "centralized_orchestration" } },
    messages: [
      message(inboundId, "inbound", "Solicitação que precisa de avaliação.", "review-turn"),
      message("canonical-reply", "outbound", "Sugestão canônica para avaliar.", "review-turn", { runtimeRunId: "canonical-run", reviewRequired: true }),
      { ...message("comparison-reply", "outbound", "Sugestão de outra arquitetura.", "review-turn", { runtimeRunId: "comparison-run", reviewRequired: true }), status: "human_review_required" },
      message("later-input", "inbound", "Outra solicitação posterior.", "later-turn"),
      message("later-reply", "outbound", "Resposta posterior sem revisão.", "later-turn"),
    ],
    attachments: [], runs: [], events: [],
    reviewTasks: [{ id: taskId, conversationId, messageId: inboundId, status, reason: "Avaliação humana necessária", createdAt: timestamp, metadata: { runtimeRunId: "canonical-run" } }],
  };
}

async function setup(page: Page, status: "open" | "resolved" | "cancelled") {
  await installMockEventSource(page);
  await mockFrontendApi(page);
  const data = detail(status);
  await page.route(`**/conversations/${conversationId}`, (route) => route.fulfill({ json: data }));
  await page.route("**/reviews", (route) => route.fulfill({ json: { reviewTasks: status === "open" ? data.reviewTasks : [] } }));
}

test("pending handoff is visible in chat with direct review actions", async ({ page }) => {
  await setup(page, "open");
  await page.goto(`/?conversationId=${conversationId}`);
  const banner = page.getByTestId("human-review-banner");
  await expect(banner).toContainText("Encaminhada para revisão humana");
  await expect(banner).toContainText("A resposta sugerida aguarda uma decisão humana");
  await expect(banner.getByRole("link", { name: "Ver fila de revisão" })).toHaveAttribute("href", /#review-queue$/);
  await expect(page.getByTestId("conversation-review-status")).toContainText("Aguardando revisão humana");
  await expect(page.getByTestId("message-canonical-reply")).toContainText("Aguardando revisão humana");
  await expect(page.getByTestId("message-canonical-reply")).toContainText("Sugestão ainda não aprovada");
  await expect(page.getByTestId("message-comparison-reply")).not.toContainText("Revisão aprovada");
  await expect(page.getByTestId("message-comparison-reply")).toContainText("Comparação · atendimento em revisão");
  await banner.getByRole("button", { name: "Revisar aqui" }).click();
  await expect(page.getByTestId(`review-approve-${taskId}`)).toBeVisible();
});

test("mobile pending banner keeps its explanation and review actions readable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await setup(page, "open");
  await page.goto(`/?conversationId=${conversationId}`);
  const banner = page.getByTestId("human-review-banner");
  await expect(banner.getByRole("button", { name: "Revisar aqui" })).toBeVisible();
  await expect(banner.getByRole("link", { name: "Ver fila de revisão" })).toBeVisible();
  expect((await banner.boundingBox())!.height).toBeLessThan(180);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("header retains readable conversation title space beside review controls", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await setup(page, "open");
  await page.goto(`/?conversationId=${conversationId}`);
  const title = page.getByRole("heading", { name: "Solicitação de dose e avaliação farmacêutica", exact: true });
  await expect(title).toBeVisible();
  expect((await title.boundingBox())!.width).toBeGreaterThan(180);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

for (const status of ["resolved", "cancelled"] as const) {
  test(`${status} review labels only its bound response and clears pending attention`, async ({ page }) => {
    await setup(page, status);
    await page.goto(`/?conversationId=${conversationId}`);
    await expect(page.getByTestId("message-canonical-reply")).toContainText(status === "resolved" ? "Revisão aprovada" : "Revisão não aprovada");
    await expect(page.getByTestId("human-review-banner")).toHaveCount(0);
    await expect(page.getByTestId("conversation-review-status")).toHaveCount(0);
    await expect(page.getByTestId("message-comparison-reply")).not.toContainText("Revisão aprovada");
    await expect(page.getByTestId("message-comparison-reply")).toContainText(status === "resolved" ? "Comparação · atendimento revisado" : "Comparação · atendimento não aprovado");
    await expect(page.getByTestId("message-comparison-reply")).not.toContainText("Revisão necessária");
    await expect(page.getByTestId("message-review-status-later-reply")).toHaveCount(0);
    await expect(page.getByTestId("review-badge-link")).toBeVisible();
    await expect(page.getByTestId("review-badge-link")).toHaveAttribute("aria-label", /0 pendentes/);
    if (status === "cancelled") await expect(page.getByTestId("message-canonical-reply")).not.toContainText("Revisão aprovada");
  });
}

test("queue shows the reviewed request and bound canonical reply instead of the latest messages", async ({ page }) => {
  await setup(page, "open");
  await page.goto(`/dashboard?conversationId=${conversationId}#review-queue`);
  const task = page.getByTestId(`review-queue-task-${taskId}`);
  await expect(task).toContainText("Solicitação que precisa de avaliação");
  await expect(task).toContainText("Sugestão canônica para avaliar");
  await expect(task).not.toContainText("Sugestão de outra arquitetura");
  await expect(task).not.toContainText("Resposta posterior sem revisão");
  await expect(task).toContainText("Aguardando revisão");
  await expect(page.getByTestId("dashboard-review-summary")).toContainText("1 solicitação aguarda revisão humana");
});
