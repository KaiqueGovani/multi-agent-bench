import { expect, test, type Page } from "@playwright/test";
import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

const conversationId = mockIds.workflowConversation;
const runId = mockIds.workflowRun;
const inboundId = `${conversationId}-review-inbound`;
const outboundId = `${conversationId}-review-outbound`;
const now = "2026-11-17T21:00:00.000Z";

function reviewTask(status = "open", id = "live-review-1") {
  return {
    id, conversationId, messageId: inboundId, status,
    createdAt: now, resolvedAt: status === "resolved" ? now : null,
    reason: "Avaliação humana solicitada pelo atendimento.",
    metadata: { runtimeRunId: runId },
  };
}

function detail(resolved: boolean) {
  return {
    conversation: {
      id: conversationId, channel: "web_chat", title: "Atendimento em revisão",
      status: resolved ? "completed" : "human_review_required",
      createdAt: now, updatedAt: now, metadata: { architectureMode: "structured_workflow" },
    },
    messages: [
      { id: inboundId, conversationId, direction: "inbound", contentText: "Quero uma avaliação humana deste atendimento.", status: resolved ? "completed" : "human_review_required", correlationId: "live-review-correlation", createdAtServer: now, metadata: {} },
      // The recorded suggestion keeps its original review flag. Task resolution
      // must take precedence over this historical metadata in the UI.
      { id: outboundId, conversationId, direction: "outbound", contentText: "Sugestão encaminhada para avaliação humana.", status: "completed", correlationId: "live-review-correlation", createdAtServer: now, metadata: { runtimeRunId: runId, sourceMessageId: inboundId, architectureMode: "structured_workflow", reviewRequired: true } },
    ],
    runs: [{ id: runId, conversationId, messageId: inboundId, correlationId: "live-review-correlation", status: resolved ? "completed" : "human_review_required", humanReviewRequired: !resolved, createdAt: now, updatedAt: now, experiment: { architectureKey: "structured_workflow" }, summary: {} }],
    attachments: [], events: [], reviewTasks: [reviewTask(resolved ? "resolved" : "open")],
  };
}

async function prepare(page: Page) {
  await installMockEventSource(page);
  await mockFrontendApi(page);
}

test("a human decision from another screen updates the active chat through SSE", async ({ page }) => {
  await prepare(page);
  await page.addInitScript(() => {
    const Original = window.EventSource;
    type CapturedStream = { url: string; listeners: Map<string, Array<(event: MessageEvent) => void>> };
    const streams: CapturedStream[] = [];
    Object.assign(window, { reviewTestStreams: streams });
    class CapturedEventSource extends Original {
      constructor(url: string) {
        super(url);
        streams.push(this as unknown as CapturedStream);
      }
    }
    Object.defineProperty(window, "EventSource", { configurable: true, writable: true, value: CapturedEventSource });
  });
  let resolved = false;
  let detailRequests = 0;
  await page.route(`**/conversations/${conversationId}`, async (route) => {
    detailRequests += 1;
    await route.fulfill({ json: detail(resolved) });
  });
  await page.route(`**/conversations/${conversationId}/events`, (route) => route.fulfill({ json: [] }));
  await page.route("**/reviews", (route) => route.fulfill({ json: { reviewTasks: resolved ? [] : [reviewTask()] } }));
  await page.goto(`/?conversationId=${conversationId}`);
  await expect(page.getByTestId("human-review-banner")).toBeVisible();
  await expect(page.getByTestId(`message-review-status-${outboundId}`)).toContainText("Aguardando revisão humana");
  await expect(page.getByTestId("review-badge-link")).toHaveAttribute("aria-label", /: 1 pendente/);
  await expect.poll(() => page.evaluate(() => {
    const streams = (window as unknown as { reviewTestStreams: Array<{ url: string }> }).reviewTestStreams;
    return streams.some((stream) => stream.url.includes("/conversations/"));
  })).toBe(true);

  const requestsBeforeDecision = detailRequests;
  resolved = true;
  await page.evaluate((event) => {
    const streams = (window as unknown as { reviewTestStreams: Array<{ url: string; listeners: Map<string, Array<(message: MessageEvent) => void>> }> }).reviewTestStreams;
    for (const stream of streams.filter((item) => item.url.includes("/conversations/"))) {
      for (const listener of stream.listeners.get("processing.event") ?? []) {
        listener(new MessageEvent("processing.event", { data: JSON.stringify(event) }));
      }
    }
  }, {
    id: "external-human-resolution", conversationId, messageId: inboundId,
    eventType: "actor.completed", actorName: "human_reviewer", status: "completed",
    correlationId: "live-review-correlation", createdAt: now,
    payload: { source: "human_review", reviewTaskId: "live-review-1", resolutionStatus: "resolved", runId },
  });

  await expect.poll(() => detailRequests).toBeGreaterThan(requestsBeforeDecision);
  await expect(page.getByTestId("human-review-banner")).toHaveCount(0);
  await expect(page.getByTestId(`message-review-status-${outboundId}`)).toContainText("Revisão aprovada");
  await expect(page.getByTestId("review-badge-link")).toHaveAttribute("aria-label", /: 0 pendentes/);
});

test("returning to a draft refreshes the global review queue count", async ({ page }) => {
  await prepare(page);
  let tasks = [reviewTask()];
  await page.route("**/reviews", (route) => route.fulfill({ json: { reviewTasks: tasks } }));
  await page.goto("/");
  const queue = page.getByTestId("review-badge-link");
  await expect(queue).toHaveAttribute("aria-label", /: 1 pendente/);
  tasks = [reviewTask(), reviewTask("open", "live-review-2")];
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect(queue).toHaveAttribute("aria-label", /: 2 pendentes/);
  await expect(page.getByTestId("message-list-empty")).toBeVisible();
});

test("an older queue response cannot restore a stale pending count", async ({ page }) => {
  await prepare(page);
  let release!: () => void;
  const delayed = new Promise<void>((resolve) => { release = resolve; });
  let requests = 0;
  await page.route("**/reviews", async (route) => {
    requests += 1;
    if (requests === 1) {
      await delayed;
      return route.fulfill({ json: { reviewTasks: [reviewTask()] } });
    }
    return route.fulfill({ json: { reviewTasks: [] } });
  });
  await page.goto("/");
  await expect.poll(() => requests).toBe(1);
  try {
    await page.evaluate(() => window.dispatchEvent(new Event("focus")));
    await expect.poll(() => requests).toBeGreaterThan(1);
    const queue = page.getByTestId("review-badge-link");
    await expect(queue).toHaveAttribute("aria-label", /: 0 pendentes/);
    const staleReply = page.waitForResponse((response) => new URL(response.url()).pathname === "/reviews");
    release();
    await staleReply;
    // A further user action flushes the React update from the delayed request,
    // while remaining on the same draft and without requesting the queue again.
    await page.getByTestId("message-composer-input").fill("Rascunho preservado");
    await expect(queue).toHaveAttribute("aria-label", /: 0 pendentes/);
  } finally {
    release();
  }
});
