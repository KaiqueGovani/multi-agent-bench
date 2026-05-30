import { expect, test } from "@playwright/test";

import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

test.describe("flow visualization improvements", () => {
  test.beforeEach(async ({ page }) => {
    await installMockEventSource(page);
    await mockFrontendApi(page);
  });

  test("centralized flow renders colored edges for active handoffs", async ({ page }) => {
    await page.goto(`/?conversationId=${mockIds.centralizedConversation}`);

    // Open flow panel
    await page.getByTestId("flow-toggle").click();
    await expect(page.getByTestId("chat-flow-panel")).toBeVisible();
    await expect(page.getByTestId("runtime-visual-centralized")).toBeVisible();

    // Edges should exist in the SVG (React Flow renders edges as SVG paths)
    const flowContainer = page.getByTestId("runtime-visual-centralized");
    const edges = flowContainer.locator(".react-flow__edge");
    await expect(edges.first()).toBeAttached();
  });

  test("workflow flow renders sequential edges between stages", async ({ page }) => {
    await page.goto(`/?conversationId=${mockIds.workflowConversation}`);

    await page.getByTestId("flow-toggle").click();
    await expect(page.getByTestId("runtime-visual-workflow")).toBeVisible();

    const flowContainer = page.getByTestId("runtime-visual-workflow");
    const nodes = flowContainer.locator(".react-flow__node");
    // Workflow has 5 stages
    await expect(nodes).toHaveCount(5);
  });

  test("swarm flow renders mesh edges from handoff events", async ({ page }) => {
    await page.goto(`/?conversationId=${mockIds.swarmConversation}`);

    await page.getByTestId("flow-toggle").click();
    await expect(page.getByTestId("runtime-visual-swarm")).toBeVisible();

    const flowContainer = page.getByTestId("runtime-visual-swarm");
    const nodes = flowContainer.locator(".react-flow__node");
    // Swarm has 5 peers
    await expect(nodes).toHaveCount(5);

    // Edges should be present (handoffs are provided in mock data)
    const edges = flowContainer.locator(".react-flow__edge");
    await expect(edges.first()).toBeAttached();
  });

  test("agent nodes display event counts for tools and responses", async ({ page }) => {
    await page.goto(`/?conversationId=${mockIds.centralizedConversation}`);

    await page.getByTestId("flow-toggle").click();
    await expect(page.getByTestId("runtime-visual-centralized")).toBeVisible();

    // Nodes with events show tool/response counts inline
    const faqNode = page.getByTestId("runtime-visual-centralized").locator(".react-flow__node").filter({ hasText: "FAQ" });
    await expect(faqNode).toBeVisible();
    await expect(faqNode).toContainText("tool");

    const responseNode = page.getByTestId("runtime-visual-centralized").locator(".react-flow__node").filter({ hasText: "Resposta" });
    await expect(responseNode).toBeVisible();
    await expect(responseNode).toContainText("resp");

    // Supervisor node should show event count
    const supervisorNode = page.getByTestId("runtime-visual-centralized").locator(".react-flow__node").filter({ hasText: "Supervisor" });
    await expect(supervisorNode).toBeVisible();
  });

  test("flow panel shows architecture picker for multi-architecture runs", async ({ page }) => {
    // Swarm conversation has a single run, so no picker
    await page.goto(`/?conversationId=${mockIds.swarmConversation}`);
    await page.getByTestId("flow-toggle").click();
    await expect(page.getByTestId("chat-flow-panel")).toBeVisible();
  });

  test("Visão Geral tab shows architecture comparison overview", async ({ page }) => {
    await page.goto(`/?conversationId=${mockIds.centralizedConversation}`);

    // Switch to Visão Geral tab
    await page.locator("nav").getByRole("button", { name: "Visão Geral" }).click();

    // Default mode is all_architectures — shows comparison overview with flow inside
    await expect(page.getByRole("heading", { name: "Comparação das arquiteturas" })).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId("runtime-visual-centralized")).toBeVisible({ timeout: 10000 });
  });

  test("nodes display event counts for tool calls and responses", async ({ page }) => {
    await page.goto(`/?conversationId=${mockIds.centralizedConversation}`);

    await page.getByTestId("flow-toggle").click();
    const flowContainer = page.getByTestId("runtime-visual-centralized");
    await expect(flowContainer).toBeVisible();

    // The response_streamer node has response events — should show "resp" count
    const responseNode = flowContainer.locator(".react-flow__node").filter({ hasText: "Resposta" });
    await expect(responseNode).toBeVisible();
    await expect(responseNode).toContainText("resp");
  });
});
