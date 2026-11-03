import { expect, test } from "@playwright/test";
import { observedAgentGraph } from "../../src/components/runtime/observed-agent-graph";
import type { RunExecutionEvent } from "../../src/lib/types";
import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

function event(sequenceNo: number, eventFamily: string, eventName: string, actorName: string, payload: Record<string, unknown> = {}): RunExecutionEvent {
  return {
    id: `observed-${sequenceNo}`, runId: mockIds.centralizedRun,
    conversationId: mockIds.centralizedConversation, messageId: "synthetic-message",
    correlationId: "synthetic-correlation", sequenceNo, eventFamily, eventName,
    actorName, status: eventName === "started" ? "running" : "completed",
    createdAt: "2026-11-02T20:00:00Z", payload,
  } as RunExecutionEvent;
}

const events = [
  event(1, "agent", "started", "supervisor", { agentInvocationId: "supervisor-1" }),
  event(2, "tool", "started", "supervisor", { toolCallId: "specialist-tool", callKind: "specialist" }),
  event(3, "agent", "started", "stock", { agentInvocationId: "stock-1", parentAgentInvocationId: "supervisor-1", parentCallId: "specialist-tool" }),
  event(4, "tool", "started", "stock", { toolCallId: "domain-tool", callKind: "domain" }),
  event(5, "tool", "started", "stock", { toolCallId: "domain-tool", callKind: "domain" }),
  event(6, "tool", "completed", "stock", { toolCallId: "domain-tool", callKind: "domain", result: { quantity: 17 } }),
  event(7, "agent", "completed", "stock", { agentInvocationId: "stock-1", outputText: "Consulta controlada: dipirona, 17 frascos." }),
  event(8, "communication", "message", "stock", { to: "supervisor", text: "Consulta controlada: dipirona, 17 frascos." }),
  event(9, "tool", "completed", "supervisor", { toolCallId: "specialist-tool", callKind: "specialist" }),
  event(10, "agent", "completed", "supervisor", { agentInvocationId: "supervisor-1", outputText: "A fonte controlada informa 17 frascos de dipirona." }),
];

test("graph requires agent invocation evidence and explicit parent/return records", () => {
  const graph = observedAgentGraph([...events, event(11, "tool", "completed", "faq")], true);
  expect(graph.agents.map((agent) => agent.role)).toEqual(["supervisor", "stock"]);
  expect(graph.links).toEqual([
    { from: "supervisor", to: "stock", kind: "call", status: "completed" },
    { from: "stock", to: "supervisor", kind: "return", status: "completed" },
  ]);
  expect(observedAgentGraph([event(1, "tool", "completed", "stock")], true).agents).toEqual([]);
  const noParent = events.map((entry) => entry.sequenceNo === 3 ? { ...entry, payload: { agentInvocationId: "stock-1" } } : entry);
  expect(observedAgentGraph(noParent, true).links.map((link) => link.kind)).toEqual(["return"]);
  expect(observedAgentGraph(events.slice(0, 5), false).links[0]?.status).toBe("running");
  expect(observedAgentGraph(events.slice(0, 7), false).links[0]?.status).toBe("completed");
});

test("actual specialist and its returned text are shown without a fabricated synthesizer", async ({ page }) => {
  await installMockEventSource(page);
  await mockFrontendApi(page);
  await page.route(`**/runs/${mockIds.centralizedRun}/execution`, async (route) => {
    await route.fulfill({ json: {
      executionEvents: events,
      projection: {
        architectureMode: "centralized_orchestration", runStatus: "completed",
        architectureView: { actors: {}, stages: [], handoffs: [] }, metrics: {}, state: {},
      },
      run: {
        id: mockIds.centralizedRun, status: "completed",
        experiment: { architectureKey: "centralized_orchestration", comparisonProtocol: "architectural-comparison-v4.2" },
      },
    } });
  });
  await page.goto(`/?conversationId=${mockIds.centralizedConversation}`);
  await page.getByTestId("flow-toggle").click();
  const flow = page.getByTestId("runtime-visual-centralized");
  await expect(page.getByTestId("observed-agent-flow")).toBeVisible();
  await expect(flow.locator(".react-flow__node")).toHaveCount(2);
  await expect(flow.locator(".react-flow__edge")).toHaveCount(2);
  await expect(flow).not.toContainText("Streamer");
  await expect(flow).not.toContainText("FAQ");
  // One tool lifecycle is one invocation. A duplicate started record with the
  // same toolCallId and the completed record must not inflate the node badge.
  await expect(flow.locator(".react-flow__node").filter({ hasText: "Estoque" })).toContainText("1 tool");
  await expect(flow.locator(".react-flow__node").filter({ hasText: "Estoque" })).not.toContainText("2 tool");
  await expect(flow.locator(".react-flow__node").filter({ hasText: "Supervisor" })).toContainText("1 tool");
  await flow.locator(".react-flow__node").filter({ hasText: "Estoque" }).hover();
  await page.getByRole("button", { name: "agent.completed" }).click();
  await expect(page.getByText("Consulta controlada: dipirona, 17 frascos.", { exact: true })).toBeVisible();

  await page.keyboard.press("Escape");
  const trigger = flow.getByRole("button", { name: "Eventos de Estoque" });
  await trigger.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("region", { name: "Eventos de Estoque" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Fechar eventos" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("region", { name: "Eventos de Estoque" })).toHaveCount(0);
  await expect(trigger).toBeFocused();
});
