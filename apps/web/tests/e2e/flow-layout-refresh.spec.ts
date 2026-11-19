import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

const baseline = process.env.FLOW_REFRESH_BASELINE === "1";
const evidence = path.resolve(__dirname, "../../../../research-data/local/ui-polish");
const scenarios = [
  { key: "centralized", conversation: mockIds.centralizedConversation, run: mockIds.centralizedRun, architecture: "centralized_orchestration", roles: ["supervisor", "stock", "faq"] },
  { key: "workflow", conversation: mockIds.workflowConversation, run: mockIds.workflowRun, architecture: "structured_workflow", roles: ["router", "faq", "stock", "synthesizer"] },
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
    if (scenario.key === "workflow") add("communication", "message", "faq", { to: "synthesizer", text: "Contexto de FAQ recebido" });
    await page.route(`**/runs/${scenario.run}/execution`, (route) => route.fulfill({ json: {
      executionEvents: events,
      projection: { architectureMode: scenario.architecture, runStatus: "completed", architectureView: { actors: {}, stages: [], handoffs: [] }, metrics: {}, state: {} },
      run: { id: scenario.run, status: "completed", experiment: { architectureKey: scenario.architecture, comparisonProtocol: "architectural-comparison-v4.4" } },
    } }));
    await page.goto(`/?conversationId=${scenario.conversation}`);
    await page.getByTestId("flow-toggle").click();
    const flow = page.getByTestId(`runtime-visual-${scenario.key}`);
    await expect(flow.locator(".react-flow__node")).toHaveCount(scenario.key === "swarm" ? 5 : scenario.roles.length);
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
        expect(positions[3].x).toBeGreaterThan(positions[2].x);
        await expect(flow.locator('[data-edge-route="workflow-bypass"]')).toHaveCount(0);
        await expect(flow.locator('[data-edge-kind="sequence"]')).toHaveCount(3);
        // The stage-order connectors must stay between adjacent cards even
        // when the trace records evidence sent to a nonadjacent recipient.
        const crossedCards = await flow.locator("path.react-flow__edge-path").evaluateAll((paths) => paths.flatMap((element) => {
          const path = element as SVGPathElement;
          const matrix = path.getScreenCTM();
          if (!matrix) return ["unmeasured path"];
          const boxes = [...document.querySelectorAll('.react-flow__node')].map((node) => node.getBoundingClientRect());
          const length = path.getTotalLength();
          for (let index = 1; index < 40; index++) {
            const point = path.getPointAtLength(length * index / 40);
            const screen = new DOMPoint(point.x, point.y).matrixTransform(matrix);
            if (boxes.some((box) => screen.x > box.left + 3 && screen.x < box.right - 3 && screen.y > box.top + 3 && screen.y < box.bottom - 3)) return [path.getAttribute('d')];
          }
          return [];
        }));
        expect(crossedCards).toEqual([]);
        const outsideEdges = await flow.locator("path.react-flow__edge-path").evaluateAll((paths) => {
          const viewport = document.querySelector('[data-testid="runtime-visual-workflow"] .react-flow')!.getBoundingClientRect();
          return paths.flatMap((element) => {
            const path = element as SVGPathElement;
            const matrix = path.getScreenCTM();
            if (!matrix) return ["unmeasured path"];
            const box = path.getBBox();
            const corners = [[box.x, box.y], [box.x + box.width, box.y + box.height]].map(([x, y]) => new DOMPoint(x, y).matrixTransform(matrix));
            return corners.some((point) => point.x < viewport.left - 1 || point.x > viewport.right + 1 || point.y < viewport.top - 1 || point.y > viewport.bottom + 1) ? [path.getAttribute('d')] : [];
          });
        });
        expect(outsideEdges).toEqual([]);
      }
      if (scenario.key === "swarm") {
        const coordinator = flow.locator('.react-flow__node[data-id="coordinator"]');
        const faq = flow.locator('.react-flow__node[data-id="faq"]');
        const stock = flow.locator('.react-flow__node[data-id="stock"]');
        const attachments = flow.locator('.react-flow__node[data-id="attachments"]');
        await expect(faq.locator('[data-status]')).toHaveAttribute('data-status', 'not_invoked');
        await expect(attachments.locator('[data-status]')).toHaveAttribute('data-status', 'not_invoked');
        await expect(coordinator.locator('[data-status]')).toHaveAttribute('data-status', 'completed');
        await expect(stock.locator('[data-status]')).toHaveAttribute('data-status', 'completed');
        expect(await faq.locator('[data-status]').evaluate((node) => getComputedStyle(node).borderStyle)).toBe('dashed');
        await expect(flow.locator('.react-flow__edge')).toHaveCount(2);
        const c = (await coordinator.boundingBox())!;
        const f = (await faq.boundingBox())!;
        const s = (await stock.boundingBox())!;
        expect(c.y).toBeGreaterThan(f.y);
        expect(c.x).toBeGreaterThan(f.x);
        expect(s.x).toBeGreaterThan(c.x);
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
      if (scenario.key === "workflow") {
        expect(await flow.locator("path.react-flow__edge-path").evaluateAll((paths) => {
          const viewport = document.querySelector('[data-testid="runtime-visual-workflow"] .react-flow')!.getBoundingClientRect();
          return paths.every((element) => {
            const path = element as SVGPathElement;
            const matrix = path.getScreenCTM();
            if (!matrix) return false;
            const box = path.getBBox();
            return [[box.x, box.y], [box.x + box.width, box.y + box.height]].every(([x, y]) => {
              const point = new DOMPoint(x, y).matrixTransform(matrix);
              return point.x >= viewport.left - 1 && point.x <= viewport.right + 1 && point.y >= viewport.top - 1 && point.y <= viewport.bottom + 1;
            });
          });
        })).toBe(true);
      }
      await flow.screenshot({ path: path.join(evidence, `after-${scenario.key}-mobile.png`) });
    }
  });
}

test("swarm shows its complete neutral roster before any agent invocation", async ({ page }) => {
  await installMockEventSource(page);
  await mockFrontendApi(page);
  await page.route(`**/runs/${mockIds.swarmRun}/execution`, (route) => route.fulfill({ json: {
    executionEvents: [],
    projection: { architectureMode: 'decentralized_swarm', runStatus: 'running', architectureView: { actors: {}, handoffs: [] }, metrics: {}, state: {} },
    run: { id: mockIds.swarmRun, status: 'running', experiment: { architectureKey: 'decentralized_swarm' } },
  } }));
  await page.goto(`/?conversationId=${mockIds.swarmConversation}`);
  await page.getByTestId('flow-toggle').click();
  const flow = page.getByTestId('runtime-visual-swarm');
  await expect(flow.locator('.react-flow__node')).toHaveCount(5);
  await expect(flow.locator('[data-status="not_invoked"]')).toHaveCount(5);
  await expect(flow.locator('.react-flow__edge')).toHaveCount(0);
});
