import { expect, test } from "@playwright/test";

import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

test.describe("P1 — Streaming messages in chat UI", () => {
  test("user message appears immediately on send (optimistic)", async ({ page }) => {
    await installMockEventSource(page);
    await mockFrontendApi(page);

    await page.goto(`/?conversationId=${mockIds.swarmConversation}`);
    await expect(page.getByTestId("message-list")).toContainText("Tem dipirona em estoque?");

    // Start a new conversation to test optimistic message
    await page.getByRole("button", { name: "Nova conversa" }).click();
    await expect(page.getByTestId("message-list-empty")).toBeVisible();

    // Type and send a message
    await page.getByTestId("message-composer-input").fill("Mensagem otimista de teste");
    await page.getByRole("button", { name: "Enviar" }).click();

    // The optimistic message should appear immediately (before SSE)
    await expect(page.getByTestId("message-list")).toContainText("Mensagem otimista de teste");
  });

  test("streaming indicator appears during response.partial events", async ({ page }) => {
    await installMockEventSource(page);
    await mockFrontendApi(page);

    // Intercept EventSource to inject streaming events
    await page.addInitScript(() => {
      const originalEventSource = window.EventSource;
      class StreamingMockEventSource extends originalEventSource {
        constructor(url: string) {
          super(url);
          // After open, simulate response.partial events
          queueMicrotask(() => {
            setTimeout(() => {
              const runId = "test-streaming-run-id";
              const partialEvent = {
                id: "streaming-test-event-1",
                conversationId: url.match(/conversations\/([^/]+)/)?.[1] ?? "",
                messageId: null,
                eventType: "response.partial",
                actorName: "response_streamer",
                parentEventId: null,
                correlationId: "corr-streaming",
                payload: { contentText: "Resposta parcial...", runId },
                createdAt: new Date().toISOString(),
                durationMs: null,
                status: "running",
              };
              const listeners = (this as unknown as { listeners: Map<string, Array<(e: MessageEvent) => void>> }).listeners;
              for (const listener of listeners.get("processing.event") ?? []) {
                listener(new MessageEvent("processing.event", { data: JSON.stringify(partialEvent) }));
              }
            }, 100);
          });
        }
      }
      Object.defineProperty(window, "EventSource", {
        configurable: true,
        value: StreamingMockEventSource,
        writable: true,
      });
    });

    await page.goto(`/?conversationId=${mockIds.centralizedConversation}`);
    await expect(page.getByTestId("message-list")).toContainText("Tem dipirona em estoque?");

    // Wait for the streaming message to appear with the spinner
    const streamingMsg = page.locator("[data-testid^='message-streaming-']");
    await expect(streamingMsg).toBeVisible({ timeout: 5000 });
    await expect(streamingMsg).toContainText("Resposta parcial...");

    // Verify the Loader2 spinner is present
    const spinner = streamingMsg.locator("[aria-label='Streaming']");
    await expect(spinner).toBeVisible();
  });
});
