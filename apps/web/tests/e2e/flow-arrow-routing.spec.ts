import { expect, test, type Locator, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import type { RunExecutionEvent } from "../../src/lib/types";
import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

type Scenario = "swarm" | "workflow" | "workflow-reverse" | "workflow-exchange";
const evidence = path.resolve(__dirname, "../../../../research-data/local/ui-polish");

async function openFlow(page: Page, scenario: Scenario) {
  const swarm = scenario === "swarm";
  const conversationId = swarm ? mockIds.swarmConversation : mockIds.workflowConversation;
  const runId = swarm ? mockIds.swarmRun : mockIds.workflowRun;
  const architecture = swarm ? "decentralized_swarm" : "structured_workflow";
  const events: RunExecutionEvent[] = [];
  const add = (eventFamily: string, eventName: string, actorName: string, payload: Record<string, unknown>) => {
    events.push({
      id: `arrow-${events.length}`, sequenceNo: events.length + 1,
      runId, conversationId, messageId: "arrow-message", correlationId: "arrow-correlation",
      eventFamily, eventName, actorName, source: "ai_service",
      status: eventName === "started" ? "running" : "completed",
      createdAt: "2026-11-17T18:00:00Z", payload,
    } as RunExecutionEvent);
  };
  const invocation = (role: string, parent?: string) => {
    const payload = { agentInvocationId: `${role}-1`, ...(parent ? { parentAgentInvocationId: `${parent}-1` } : {}) };
    add("agent", "started", role, payload);
    add("agent", "completed", role, { ...payload, outputText: `Resultado de ${role}` });
  };

  if (swarm) {
    invocation("coordinator");
    invocation("faq", "coordinator");
    add("communication", "message", "faq", { to: "coordinator", text: "Retorno do especialista" });
    // The live protocol invokes synthesis with collected evidence but does not
    // record a direct communication to it. The UI must distinguish that order.
    invocation("synthesizer");
  } else {
    invocation("router");
    invocation("faq");
    add("communication", "message", "faq", { to: "synthesizer", text: "Evidência para síntese" });
    invocation("synthesizer");
    if (scenario === "workflow-reverse") {
      add("communication", "message", "synthesizer", { to: "router", text: "Retorno ao início do fluxo" });
    } else if (scenario === "workflow-exchange") {
      add("communication", "message", "synthesizer", { to: "faq", text: "Retorno para o especialista" });
    }
  }

  await installMockEventSource(page);
  await mockFrontendApi(page);
  await page.route(`**/runs/${runId}/execution`, (route) => route.fulfill({ json: {
    executionEvents: events,
    projection: { architectureMode: architecture, runStatus: "completed", architectureView: { actors: {}, stages: [], handoffs: [] }, metrics: {}, state: {} },
    run: { id: runId, status: "completed", experiment: { architectureKey: architecture, comparisonProtocol: "architectural-comparison-v4.4" } },
  } }));
  await page.goto(`/?conversationId=${conversationId}`);
  await page.getByTestId("flow-toggle").click();
  const flow = page.getByTestId(`runtime-visual-${swarm ? "swarm" : "workflow"}`);
  await expect(flow.locator(".react-flow__node")).toHaveCount(swarm ? 5 : 3);
  await expect(flow.locator("path.react-flow__edge-path")).toHaveCount(scenario === "workflow-reverse" ? 3 : 2);
  return flow;
}

/** Check the actual SVG geometry, including its fitted viewport transform. */
async function geometryProblems(flow: Locator) {
  return flow.evaluate((root) => {
    const viewport = root.querySelector(".react-flow")!.getBoundingClientRect();
    const panel = root.closest('[data-testid="chat-flow-panel"]')!;
    const panelBox = panel.getBoundingClientRect();
    const visibleChat = panel.parentElement!.getBoundingClientRect();
    // A large internal canvas can contain every node while the chat panel or
    // composer clips it. Check the intersection that the user can really see.
    const visible = {
      left: Math.max(viewport.left, panelBox.left, visibleChat.left, 0),
      top: Math.max(viewport.top, panelBox.top, visibleChat.top, 0),
      right: Math.min(viewport.right, panelBox.right, visibleChat.right, innerWidth),
      bottom: Math.min(viewport.bottom, panelBox.bottom, visibleChat.bottom, innerHeight),
    };
    const cards = [...root.querySelectorAll(".react-flow__node")].map((node) => ({
      id: node.getAttribute("data-id"), box: node.getBoundingClientRect(),
    }));
    const problems: string[] = [];
    for (const { id, box } of cards) {
      if (box.left < visible.left - 1 || box.top < visible.top - 1 || box.right > visible.right + 1 || box.bottom > visible.bottom + 1) {
        problems.push(`card outside visible chat panel: ${id}`);
      }
    }
    for (const element of root.querySelectorAll("path.react-flow__edge-path")) {
      const edge = element as SVGPathElement;
      const matrix = edge.getScreenCTM();
      if (!matrix) {
        problems.push("unmeasured edge");
        continue;
      }
      const edgeId = edge.closest(".react-flow__edge")?.getAttribute("data-id");
      const scale = Math.hypot(matrix.a, matrix.b);
      const length = edge.getTotalLength();
      for (let index = 0; index <= 100; index++) {
        const local = edge.getPointAtLength(length * index / 100);
        const point = new DOMPoint(local.x, local.y).matrixTransform(matrix);
        if (point.x < visible.left + 1 || point.y < visible.top + 1 || point.x > visible.right - 1 || point.y > visible.bottom - 1) {
          problems.push(`edge outside visible chat panel: ${edgeId}`);
          break;
        }
        if (cards.some(({ box }) => point.x > box.left + 1 && point.x < box.right - 1 && point.y > box.top + 1 && point.y < box.bottom - 1)) {
          problems.push(`edge crosses card: ${edgeId}`);
          break;
        }
      }
      for (const [attribute, at] of [["marker-start", 0], ["marker-end", length]] as const) {
        const value = edge.getAttribute(attribute);
        if (!value || value === "none") continue;
        const markerId = value.match(/#([^)]*)\)/)?.[1];
        const marker = markerId ? document.getElementById(markerId) : null;
        if (!marker) {
          problems.push(`missing arrowhead definition: ${edgeId} ${attribute}`);
          continue;
        }
        const local = edge.getPointAtLength(at);
        const point = new DOMPoint(local.x, local.y).matrixTransform(matrix);
        const nearestCard = Math.min(...cards.map(({ box }) => Math.hypot(
          Math.max(box.left - point.x, 0, point.x - box.right),
          Math.max(box.top - point.y, 0, point.y - box.bottom),
        )));
        if (nearestCard < 3 * scale) problems.push(`arrowhead touches card: ${edgeId} ${attribute}`);
        const radius = Number(marker.getAttribute("markerWidth") ?? "0") * scale;
        if (point.x - radius < visible.left || point.y - radius < visible.top || point.x + radius > visible.right || point.y + radius > visible.bottom) {
          problems.push(`arrowhead clipped: ${edgeId} ${attribute}`);
        }
      }
    }
    return problems;
  });
}

for (const viewport of [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "short-desktop", width: 1280, height: 720 },
  { name: "narrow", width: 390, height: 844 },
]) {
  const scenarios: Scenario[] = ["swarm", "workflow", "workflow-reverse"];
  if (viewport.name === "desktop") scenarios.push("workflow-exchange");
  for (const scenario of scenarios) {
    test(`${scenario} arrows remain legible and contained on ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      const flow = await openFlow(page, scenario);
      const sequence = flow.locator('[data-edge-kind="sequence"]');
      const communication = flow.locator('[data-edge-kind="communication"]');
      await expect(sequence).toHaveCount(1);
      await expect(sequence).toHaveAttribute("data-edge-state", /^(settled|recent)$/);
      await expect(sequence.locator("path.react-flow__edge-path")).toHaveCSS("stroke-dasharray", /[1-9]/);
      await expect(communication).toHaveCount(scenario === "workflow-reverse" ? 2 : 1);

      if (scenario === "swarm") {
        await expect(communication).toHaveAttribute("data-edge-direction", "both");
        const callAndReturn = communication.locator("path.react-flow__edge-path");
        await expect(callAndReturn).toHaveAttribute("marker-start", /url\(#.+\)/);
        await expect(callAndReturn).toHaveAttribute("marker-end", /url\(#.+\)/);
        await expect(communication).toHaveAttribute("data-edge-route", "swarm-direct");
        await expect(flow.locator('.react-flow__node[data-id="stock"] [data-status]')).toHaveAttribute("data-status", "not_invoked");
        await expect(flow.locator('.react-flow__node[data-id="attachments"] [data-status]')).toHaveAttribute("data-status", "not_invoked");
        const edges = await flow.locator(".react-flow__edge").evaluateAll((elements) => elements.map((edge) => ({
          id: edge.getAttribute("data-id"), kind: edge.querySelector("[data-edge-kind]")?.getAttribute("data-edge-kind"),
        })));
        expect(edges.every(({ id }) => !/stock|attachments/.test(id ?? ""))).toBe(true);
        expect(edges.some(({ id, kind }) => id?.includes("synthesizer") && kind === "sequence")).toBe(true);
        expect(edges.some(({ id, kind }) => id?.includes("synthesizer") && kind === "communication")).toBe(false);
      } else {
        await expect(sequence).toHaveAttribute("data-edge-route", "workflow-forward");
        await expect(sequence).toHaveAttribute("data-edge-direction", "forward");
        if (scenario === "workflow-reverse") {
          await expect(flow.locator('[data-edge-route="workflow-bypass"]')).toHaveCount(1);
        } else if (scenario === "workflow-exchange") {
          await expect(communication).toHaveAttribute("data-edge-direction", "both");
          const exchange = communication.locator("path.react-flow__edge-path");
          await expect(exchange).toHaveAttribute("marker-start", /url\(#.+\)/);
          await expect(exchange).toHaveAttribute("marker-end", /url\(#.+\)/);
          await expect(communication).toHaveAttribute("data-edge-route", "workflow-forward");
        }
      }
      await expect.poll(() => geometryProblems(flow)).toEqual([]);
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      fs.mkdirSync(evidence, { recursive: true });
      await flow.screenshot({ path: path.join(evidence, `flow-arrow-${scenario}-${viewport.name}.png`) });
    });
  }
}
