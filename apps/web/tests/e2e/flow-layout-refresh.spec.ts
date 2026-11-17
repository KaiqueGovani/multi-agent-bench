import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

const baseline = process.env.FLOW_REFRESH_BASELINE === "1";
const evidence = path.resolve(__dirname, "../../../../research-data/local/ui-refresh");
const scenarios = [
  { key: "centralized", conversation: mockIds.centralizedConversation, run: mockIds.centralizedRun, architecture: "centralized_orchestration", roles: ["supervisor", "stock", "faq"] },
  { key: "workflow", conversation: mockIds.workflowConversation, run: mockIds.workflowRun, architecture: "structured_workflow", roles: ["router", "stock", "synthesizer"] },
  { key: "swarm", conversation: mockIds.swarmConversation, run: mockIds.swarmRun, architecture: "decentralized_swarm", roles: ["coordinator", "stock", "synthesizer"] },
];

for (const scenario of scenarios) {
  test(`${scenario.key} keeps observed agents visible in its architecture layout`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await installMockEventSource(page);
    await mockFrontendApi(page);
    const events: Record<string, unknown>[] = [];
    const add = (family: string, name: string, role: string, payload: Record<string, unknown> = {}) => events.push({
      id: `${scenario.key}-${events.length}`, sequenceNo: events.length + 1,
      runId: scenario.run, conversationId: scenario.conversation, messageId: "refresh-message",
      correlationId: "refresh-correlation", eventFamily: family, eventName: name, actorName: role,
      status: name === "started" ? "running" : "completed", source: "ai_service",
      createdAt: "2026-11-17T15:00:00Z", payload,
    });
    for (const [index, role] of scenario.roles.entries()) {
      add("agent", "started", role, { agentInvocationId: `${role}-1`, ...(index > 0 && scenario.key === "centralized" || index === 1 && scenario.key === "swarm" ? { parentAgentInvocationId: `${scenario.roles[0]}-1` } : {}) });
      add("agent", "completed", role, { agentInvocationId: `${role}-1`, outputText: `Resultado de ${role}` });
      if (index > 0 && scenario.key === "centralized") add("communication", "message", role, { to: scenario.roles[0], text: "Retorno registrado" });
    }
    if (scenario.key !== "centralized") add("communication", "message", "stock", { to: "synthesizer", text: "Evidência recebida" });
    await page.route(`**/runs/${scenario.run}/execution`, (route) => route.fulfill({ json: {
      executionEvents: events,
      projection: { architectureMode: scenario.architecture, runStatus: "completed", architectureView: { actors: {}, stages: [], handoffs: [] }, metrics: {}, state: {} },
      run: { id: scenario.run, status: "completed", experiment: { architectureKey: scenario.architecture, comparisonProtocol: "architectural-comparison-v4.4" } },
    } }));
    await page.goto(`/?conversationId=${scenario.conversation}`);
    await page.getByTestId("flow-toggle").click();
    const flow = page.getByTestId(`runtime-visual-${scenario.key}`);
    await expect(flow.locator(".react-flow__node")).toHaveCount(3);
    await expect(flow.locator(".react-flow__node").first()).toBeVisible();
    await expect.poll(async () => {
      const area = await flow.locator(".react-flow").boundingBox();
      const boxes = await flow.locator(".react-flow__node").all();
      if (!area) return false;
      return (await Promise.all(boxes.map(async (node) => {
        const b = await node.boundingBox();
        return b && b.x >= area.x - 1 && b.y >= area.y - 1 && b.x + b.width <= area.x + area.width + 1 && b.y + b.height <= area.y + area.height + 1;
      }))).every(Boolean);
    }).toBe(true);
    fs.mkdirSync(evidence, { recursive: true });
    await flow.screenshot({ path: path.join(evidence, `${baseline ? "before" : "after"}-${scenario.key}-desktop.png`) });
    if (!baseline) {
      const positions = await flow.locator(".react-flow__node").evaluateAll((elements) => elements.map((element) => ({ x: element.getBoundingClientRect().x, y: element.getBoundingClientRect().y })));
      if (scenario.key === "workflow") {
        expect(new Set(positions.map(({ y }) => Math.round(y))).size).toBe(1);
        expect(positions[1].x).toBeGreaterThan(positions[0].x);
        expect(positions[2].x).toBeGreaterThan(positions[1].x);
      }
      if (scenario.key === "swarm") {
        expect(positions[0].y).toBeGreaterThan(positions[1].y);
        expect(positions[0].x).toBeGreaterThan(positions[1].x);
        expect(positions[2].x).toBeGreaterThan(positions[0].x);
      }
      if (scenario.key === "centralized") {
        await expect(flow.locator(".react-flow__edge")).toHaveCount(2);
        await expect(flow).toContainText("retorno recebido");
      }
      await page.setViewportSize({ width: 390, height: 844 });
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await expect(flow.getByRole("button", { name: "Ajustar fluxo" })).toBeVisible();
      await expect.poll(async () => {
        const area = await flow.locator(".react-flow").boundingBox();
        const boxes = await flow.locator(".react-flow__node").all();
        if (!area) return false;
        return (await Promise.all(boxes.map(async (node) => {
          const b = await node.boundingBox();
          return b && b.x >= area.x - 1 && b.y >= area.y - 1 && b.x + b.width <= area.x + area.width + 1 && b.y + b.height <= area.y + area.height + 1;
        }))).every(Boolean);
      }).toBe(true);
      await flow.screenshot({ path: path.join(evidence, `after-${scenario.key}-mobile.png`) });
    }
  });
}
