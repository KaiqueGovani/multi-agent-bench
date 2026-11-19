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

const stockEvidence = "Fonte de estoque controlada: 23 caixas; preço não informado.";
const faqEvidence = "Fonte FAQ controlada: prazo geral de até 90 minutos, sem confirmar pedido.";
const workflowEvents = [
  event(1, "agent", "started", "router", { agentInvocationId: "router-1" }),
  event(2, "agent", "completed", "router", { agentInvocationId: "router-1" }),
  event(3, "agent", "started", "stock", { agentInvocationId: "stock-1" }),
  event(4, "agent", "completed", "stock", { agentInvocationId: "stock-1", outputText: stockEvidence }),
  event(5, "communication", "message", "stock", { to: "synthesizer", text: stockEvidence }),
  event(6, "agent", "started", "faq", { agentInvocationId: "faq-1" }),
  event(7, "agent", "completed", "faq", { agentInvocationId: "faq-1", outputText: faqEvidence }),
  event(8, "communication", "message", "faq", { to: "synthesizer", text: faqEvidence }),
  event(9, "agent", "started", "synthesizer", { agentInvocationId: "synthesizer-1" }),
  event(10, "agent", "completed", "synthesizer", { agentInvocationId: "synthesizer-1", outputText: "Resposta final com as duas evidências." }),
].map((entry) => ({ ...entry, runId: mockIds.workflowRun, conversationId: mockIds.workflowConversation }));

test("workflow presentation preserves recorded evidence links without inventing specialist handoffs", () => {
  const graph = observedAgentGraph([...workflowEvents].reverse(), true);
  expect(graph.agents.map((agent) => agent.role)).toEqual(["router", "stock", "faq", "synthesizer"]);
  expect(graph.links).toEqual([
    { from: "stock", to: "synthesizer", kind: "return", status: "completed" },
    { from: "faq", to: "synthesizer", kind: "return", status: "completed" },
  ]);
  expect(graph.links.some((link) => link.from === "stock" && link.to === "faq")).toBe(false);
});

test("workflow shows one execution chain and keeps specialist evidence in synthesis details", async ({ page }) => {
  await installMockEventSource(page);
  await mockFrontendApi(page);
  await page.route(`**/runs/${mockIds.workflowRun}/execution`, (route) => route.fulfill({ json: {
    executionEvents: workflowEvents,
    projection: {
      architectureMode: "structured_workflow", runStatus: "completed",
      architectureView: { actors: {}, stages: [], handoffs: [] }, metrics: {}, state: {},
    },
    run: {
      id: mockIds.workflowRun, status: "completed",
      experiment: { architectureKey: "structured_workflow", comparisonProtocol: "architectural-comparison-v4.4" },
    },
  } }));
  await page.goto(`/?conversationId=${mockIds.workflowConversation}`);
  await page.getByTestId("flow-toggle").click();
  const flow = page.getByTestId("runtime-visual-workflow");
  await expect(flow.locator(".react-flow__node")).toHaveCount(4);
  await expect(flow.locator(".react-flow__edge")).toHaveCount(3);
  await expect(flow.locator('[data-edge-kind="communication"]')).toHaveCount(0);
  await expect(flow.locator('[data-edge-route="workflow-bypass"]')).toHaveCount(0);
  expect(await flow.locator(".react-flow__edge").evaluateAll((elements) => elements.map((edge) => edge.getAttribute("data-id")))).toEqual([
    "router-stock-sequence", "stock-faq-sequence", "faq-synthesizer-sequence",
  ]);
  for (const edge of await flow.locator('[data-edge-kind="sequence"]').all()) {
    await expect(edge.locator("path.react-flow__edge-path")).toHaveCSS("stroke-dasharray", "none");
  }

  await flow.getByRole("button", { name: "Eventos de Sintetizador", exact: true }).click();
  const incoming = page.getByTestId("workflow-evidence-inputs");
  await expect(incoming).toContainText("Evidências para a síntese");
  await incoming.getByText("Estoque · evento #5", { exact: true }).click();
  await expect(incoming.getByText(stockEvidence, { exact: true })).toBeVisible();
  await incoming.getByText("FAQ · evento #8", { exact: true }).click();
  await expect(incoming.getByText(faqEvidence, { exact: true })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(incoming).toHaveCount(0);
});

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
  await expect(flow.locator(".react-flow__edge")).toHaveCount(1);
  await expect(flow).toContainText("retorno recebido");
  await expect(flow).not.toContainText("Streamer");
  await expect(flow).not.toContainText("FAQ");
  // One tool lifecycle is one invocation. A duplicate started record with the
  // same toolCallId and the completed record must not inflate the node badge.
  await expect(flow.locator(".react-flow__node").filter({ hasText: "Estoque" })).toContainText("1 tool");
  await expect(flow.locator(".react-flow__node").filter({ hasText: "Estoque" })).not.toContainText("2 tool");
  await expect(flow.locator(".react-flow__node").filter({ hasText: "Orquestrador" })).toContainText("1 tool");
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

  // The observed trace uses "supervisor", while legacy processing events use
  // "supervisor_agent". Both render the same label without changing filter IDs.
  await page.getByRole("button", { name: "Atividade", exact: true }).click();
  const activity = page.getByTestId("activity-panel");
  await expect(activity.getByTestId("activity-event").getByText("Orquestrador", { exact: true })).toBeVisible();
  await expect(activity).not.toContainText("Supervisor");
  await activity.getByRole("button", { name: "Filtros", exact: true }).click();
  const actor = activity.getByRole("combobox", { name: "Ator", exact: true });
  await expect(actor.getByRole("option", { name: "Orquestrador", exact: true })).toHaveAttribute("value", "supervisor_agent");
  await actor.selectOption("supervisor_agent");
  await expect(activity.getByTestId("activity-event")).toHaveCount(1);
  await expect(activity.getByTestId("activity-event")).toContainText("Orquestrador");
});
