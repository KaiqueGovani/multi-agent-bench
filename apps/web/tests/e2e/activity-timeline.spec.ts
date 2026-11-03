import { expect, test } from "@playwright/test";

import type { ProcessingEvent } from "../../src/lib/types";
import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

test("activity follows live events without losing the reader's place or mislabeling failed steps", async ({ page }) => {
  await installMockEventSource(page);
  await mockFrontendApi(page);
  await page.addInitScript(() => {
    class ActivityEventSource extends window.EventSource {
      constructor(url: string | URL) {
        super(url);
        if (!String(url).includes("/conversations/")) return;
        window.addEventListener("activity-test-event", (event) => {
          const data = JSON.stringify((event as CustomEvent).detail);
          const { listeners } = this as unknown as { listeners: Map<string, Array<(event: MessageEvent) => void>> };
          for (const listener of listeners.get("processing.event") ?? []) {
            listener(new MessageEvent("processing.event", { data }));
          }
        });
      }
    }
    window.EventSource = ActivityEventSource;
  });

  const conversationId = mockIds.centralizedConversation;
  await page.goto(`/?conversationId=${conversationId}`);
  await page.getByRole("button", { name: "Atividade", exact: true }).click();
  const panel = page.getByTestId("activity-panel");
  const rows = panel.getByTestId("activity-event");
  await expect(panel.getByText("conectado", { exact: true })).toBeVisible();

  function event(id: number, values: Partial<ProcessingEvent> = {}): ProcessingEvent {
    return {
      id: `activity-${id}`,
      conversationId,
      correlationId: "shared-correlation",
      createdAt: new Date(Date.UTC(2030, 0, 1, 0, 0, id)).toISOString(),
      eventType: "actor.progress",
      actorName: "stock_agent",
      payload: { runId: "run-a", eventFamily: "tool", eventName: "started", toolCallId: `tool-${id}` },
      status: "running",
      ...values,
    };
  }

  async function deliver(...events: ProcessingEvent[]) {
    await page.evaluate((serialized) => {
      for (const detail of JSON.parse(serialized) as unknown[]) {
        window.dispatchEvent(new CustomEvent("activity-test-event", { detail }));
      }
    }, JSON.stringify(events));
  }

  await deliver(...Array.from({ length: 10 }, (_, i) => event(i + 1, {
    eventType: "actor.completed",
    payload: { runId: "run-a", reason: `Etapa histórica ${i + 1}` },
    status: "completed",
  })), event(11));
  const tool = rows.filter({ hasText: "tool.started" });
  await expect(tool).toContainText("Em execução");
  const follow = panel.getByRole("button", { name: "Acompanhar ao vivo" });
  await expect(follow).toHaveAttribute("aria-pressed", "true");

  const viewport = panel.getByTestId("activity-scroll");
  await viewport.evaluate((element) => { element.scrollTop = 0; });
  await expect(follow).toHaveAttribute("aria-pressed", "false");
  await deliver(event(12, {
    eventType: "actor.failed",
    payload: { runId: "run-b", eventFamily: "run", eventName: "failed" },
    status: "failed",
  }));
  await expect(rows.getByText("Falhou", { exact: true })).toHaveCount(1);
  expect(await viewport.evaluate((element) => element.scrollTop)).toBe(0);
  await expect(tool).toContainText("Em execução");

  await follow.click();
  await expect.poll(() => viewport.evaluate((element) => element.scrollHeight - element.clientHeight - element.scrollTop)).toBeLessThan(2);
  await panel.getByRole("button", { name: "Filtros", exact: true }).click();
  await panel.getByRole("combobox", { name: "Tipo", exact: true }).selectOption("tool.started");
  await deliver(event(13, {
    eventType: "actor.failed",
    payload: { runId: "run-a", eventFamily: "run", eventName: "failed" },
    status: "failed",
  }));
  await expect(tool).toContainText("Registrado");
  await expect(tool).not.toContainText("Concluído");
  await expect(panel.getByText("0 etapas ativas", { exact: false })).toBeVisible();
  await expect(rows.getByText("Falhou", { exact: true })).toHaveCount(0);

  const detail = tool.getByRole("button", { name: "Dados do evento tool.started" });
  await detail.focus();
  await page.keyboard.press("Enter");
  await expect(detail).toHaveAttribute("aria-expanded", "true");
  await expect(tool.getByLabel("JSON de tool.started")).toContainText("tool-11");
  await expect(follow).toHaveAttribute("aria-pressed", "false");
});
