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
  test(`renders user runtime summary for ${scenario.title}`, async ({ page }) => {
    await installMockEventSource(page);
    await mockFrontendApi(page);

    await page.goto(`/?conversationId=${scenario.conversationId}`);

    await expect(page.getByTestId("runtime-panel-user")).toBeVisible();
    await expect(page.getByTestId("runtime-summary-toggle")).toContainText("Ver acompanhamento");
    await expect(page.getByText("Monitor técnico do runtime")).toHaveCount(0);
    await expect(page.getByText("Ver detalhes técnicos")).toHaveCount(0);

    await page.getByTestId("runtime-summary-toggle").click();

    await expect(page.getByText("Resumo da run")).toBeVisible();
    await expect(page.getByTestId(scenario.testId)).toBeVisible();
  });
}
