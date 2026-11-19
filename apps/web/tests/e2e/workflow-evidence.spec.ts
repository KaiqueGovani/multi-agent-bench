import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import fs from "node:fs";
import path from "node:path";
import type { RunExecutionEvent } from "../../src/lib/types";
import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

const evidenceDirectory = path.resolve(__dirname, "../../../../var/workflow-sequence-qa");

function event(sequenceNo: number, family: string, name: string, actor: string, payload: Record<string, unknown> = {}, legacy = false): RunExecutionEvent {
  return {
    id: `evidence-${sequenceNo}`, sequenceNo, runId: mockIds.workflowRun,
    conversationId: mockIds.workflowConversation, messageId: "evidence-message",
    correlationId: "evidence-correlation", eventFamily: family, eventName: name,
    actorName: actor, payload, source: legacy ? "mock" : "ai_service",
    status: name === "started" ? "running" : "completed", createdAt: "2026-11-19T15:00:00Z",
  } as RunExecutionEvent;
}

function observedTrace(incoming: RunExecutionEvent[] = []) {
  return [
    event(1, "agent", "started", "router", { agentInvocationId: "router-1" }),
    event(2, "agent", "completed", "router", { agentInvocationId: "router-1" }),
    event(3, "agent", "started", "stock", { agentInvocationId: "stock-1" }),
    event(4, "agent", "completed", "stock", { agentInvocationId: "stock-1", outputText: "Saída do especialista não prova entrega de evidência." }),
    ...incoming,
    event(20, "agent", "started", "synthesizer", { agentInvocationId: "synthesizer-1" }),
    event(21, "agent", "completed", "synthesizer", { agentInvocationId: "synthesizer-1", outputText: "Saída final própria do Sintetizador." }),
  ];
}

async function openWorkflow(page: Page, executionEvents: RunExecutionEvent[], stages: Record<string, unknown>[] = []) {
  await installMockEventSource(page);
  await mockFrontendApi(page);
  await page.route(`**/runs/${mockIds.workflowRun}/execution`, (route) => route.fulfill({ json: {
    executionEvents,
    projection: {
      architectureMode: "structured_workflow", runStatus: "completed",
      architectureView: { actors: {}, stages, handoffs: [] }, metrics: {}, state: {},
    },
    run: {
      id: mockIds.workflowRun, status: "completed",
      experiment: { architectureKey: "structured_workflow", comparisonProtocol: "architectural-comparison-v4.4" },
    },
  } }));
  await page.goto(`/?conversationId=${mockIds.workflowConversation}`);
  await page.getByTestId("flow-toggle").click();
  const flow = page.getByTestId("runtime-visual-workflow");
  await expect(flow).toBeVisible();
  return flow;
}

test("synthesis details do not invent evidence from outputs or messages sent elsewhere", async ({ page }) => {
  const events = observedTrace([
    event(5, "communication", "message", "stock", { to: "router", text: "Mensagem destinada ao Roteador." }),
    event(6, "communication", "message", "synthesizer", { to: "synthesizer", text: "Autorrelato não é evidência recebida de outro agente." }),
    event(7, "communication", "completed", "stock", { to: "synthesizer", text: "Evento de outra espécie." }),
  ]);
  const flow = await openWorkflow(page, events);
  await flow.getByRole("button", { name: "Eventos de Sintetizador", exact: true }).click();
  const incoming = page.getByTestId("workflow-evidence-inputs");
  await expect(incoming).toContainText("Nenhuma evidência recebida registrada.");
  await expect(incoming.locator(":scope > details")).toHaveCount(0);
  await expect(incoming).not.toContainText("Saída do especialista");
  await expect(incoming).not.toContainText("Saída final própria");
  await expect(incoming).not.toContainText("Mensagem destinada");
});

for (const viewport of [
  { name: "desktop", width: 1280, height: 720 },
  { name: "mobile", width: 390, height: 844 },
]) {
  test(`long evidence stays literal, bounded and keyboard accessible on ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    const text = Array.from({ length: 18 }, (_, index) => `Linha ${String(index + 1).padStart(2, "0")}: evidência fictícia controlada.`).join("\n")
      + '\n<img src=x onerror="document.documentElement.dataset.evidenceExecuted=\'yes\'">\n<script>document.documentElement.dataset.evidenceExecuted="yes"</script>';
    const flow = await openWorkflow(page, observedTrace([
      event(5, "communication", "message", "stock", { to: "synthesizer", text }),
      event(6, "communication", "message", "stock", { to: "router", text: "Texto que não deve entrar na síntese." }),
    ]));
    const synthesis = flow.locator('.react-flow__node[data-id="synthesizer"]');
    await expect(synthesis).toContainText("2 evt");
    const trigger = flow.getByRole("button", { name: "Eventos de Sintetizador", exact: true });
    await trigger.focus();
    await page.keyboard.press("Enter");
    const region = page.getByRole("region", { name: "Eventos de Sintetizador", exact: true });
    await expect(region.getByRole("button", { name: "Fechar eventos" })).toBeFocused();
    const incoming = page.getByTestId("workflow-evidence-inputs");
    await expect(incoming.locator(":scope > details")).toHaveCount(1);
    const summary = incoming.getByText("Estoque · evento #5", { exact: true });
    await summary.focus();
    await page.keyboard.press("Enter");
    await expect(incoming.locator(":scope > details")).toHaveAttribute("open", "");
    const content = incoming.locator("p.whitespace-pre-wrap");
    await expect(content).toBeVisible();
    expect(await content.textContent()).toBe(text);
    await expect(incoming.locator("img, script")).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.dataset.evidenceExecuted)).toBeUndefined();
    expect(await content.evaluate((element) => element.scrollHeight > element.clientHeight)).toBe(true);
    const box = (await region.boundingBox())!;
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.y).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(viewport.width);
    expect(box.y + box.height).toBeLessThanOrEqual(viewport.height);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    fs.mkdirSync(evidenceDirectory, { recursive: true });
    await page.screenshot({ path: path.join(evidenceDirectory, `synthesis-evidence-${viewport.name}.png`) });
    await page.keyboard.press("Escape");
    await expect(region).toHaveCount(0);
    await expect(trigger).toBeFocused();
  });
}

test("legacy synthesis alias receives recorded evidence without inflating its own event count", async ({ page }) => {
  const events = [
    event(1, "node", "started", "router_agent", { stage: "classify" }, true),
    event(2, "node", "completed", "router_agent", { stage: "classify" }, true),
    event(3, "node", "completed", "stock_agent", { stage: "gather_evidence" }, true),
    event(4, "communication", "message", "stock_agent", { to: "synthesis_agent", text: "Evidência enviada ao alias legado da síntese." }, true),
    event(5, "node", "started", "synthesis_agent", { stage: "synthesize" }, true),
    event(6, "node", "completed", "synthesis_agent", { stage: "synthesize" }, true),
  ];
  const stages = [
    { stage: "classify", actorName: "router_agent", status: "completed" },
    { stage: "gather_evidence", actorName: "stock_agent", status: "completed" },
    { stage: "multimodal_analysis", actorName: "image_intake_agent", status: "not_applicable" },
    { stage: "review_gate", actorName: "review_agent", status: "completed" },
    { stage: "synthesize", actorName: "synthesis_agent", status: "completed" },
  ];
  const flow = await openWorkflow(page, events, stages);
  await expect(flow.locator(".react-flow__node")).toHaveCount(5);
  const synthesis = flow.locator('.react-flow__node[data-id="workflow_synthesis_agent"]');
  await expect(synthesis).toContainText("2 evt");
  await synthesis.getByRole("button", { name: "Eventos de Síntese", exact: true }).click();
  const incoming = page.getByTestId("workflow-evidence-inputs");
  await incoming.getByText("Estoque · evento #4", { exact: true }).click();
  await expect(incoming.getByText("Evidência enviada ao alias legado da síntese.", { exact: true })).toBeVisible();
});

test("synthesis evidence details have no automated accessibility violations", async ({ page }) => {
  const flow = await openWorkflow(page, observedTrace([
    event(5, "communication", "message", "stock", { to: "synthesizer", text: "Fonte controlada: 23 caixas; preço não informado." }),
  ]));
  await flow.getByRole("button", { name: "Eventos de Sintetizador", exact: true }).click();
  await page.getByTestId("workflow-evidence-inputs").getByText("Estoque · evento #5", { exact: true }).click();
  const report = await new AxeBuilder({ page }).include('[role="region"][aria-label="Eventos de Sintetizador"]').analyze();
  expect(report.violations).toEqual([]);
});
