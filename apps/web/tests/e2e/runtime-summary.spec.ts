import { expect, test } from "@playwright/test";

import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

const architectureCases = [
  {
    conversationId: mockIds.centralizedConversation,
    testId: "runtime-visual-centralized",
    title: "centralized orchestration",
  },
  {
    conversationId: mockIds.workflowConversation,
    testId: "runtime-visual-workflow",
    title: "structured workflow",
  },
  {
    conversationId: mockIds.swarmConversation,
    testId: "runtime-visual-swarm",
    title: "decentralized swarm",
  },
] as const;

for (const scenario of architectureCases) {
  test(`renders architecture flow for ${scenario.title} in Visão Geral tab`, async ({ page }) => {
    await installMockEventSource(page);
    await mockFrontendApi(page);

    await page.goto(`/?conversationId=${scenario.conversationId}`);

    // Switch to Visão Geral tab
    await page.locator("nav").getByRole("button", { name: "Visão Geral" }).click();

    // Default architecture mode is all_architectures — comparison overview renders
    // which shows flow visualizations for each architecture column
    await expect(page.getByRole("heading", { name: "Comparação das arquiteturas" })).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId(scenario.testId)).toBeVisible({ timeout: 10000 });
  });
}
