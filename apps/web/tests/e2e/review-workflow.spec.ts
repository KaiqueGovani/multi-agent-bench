import { expect, test } from "@playwright/test";

import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

test.describe("review workflow", () => {
  test.beforeEach(async ({ page }) => {
    await installMockEventSource(page);
    await mockFrontendApi(page);
    await page.route("http://localhost:8000/**", (route) =>
      route.fallback({
        url: route.request().url().replace("http://localhost:8000", "http://127.0.0.1:8000"),
      }),
    );
  });

  test("badge visible in header when open review tasks exist", async ({ page }) => {
    await page.goto("/");

    // The mock fixtures include one open review task for the workflow conversation
    const badge = page.getByTestId("review-badge-link");
    await expect(badge).toBeVisible();
    await expect(badge).toContainText("1");
  });

  test("approve review task from chat ReviewPanel", async ({ page }) => {
    // Navigate to the workflow conversation that has a review task
    await page.goto(`/?conversationId=${mockIds.workflowConversation}`);

    // Switch to the "Atividade" tab to see the ReviewPanel
    await page.getByRole("button", { name: "Atividade" }).click();

    // The review panel should show the open task
    await expect(page.getByText("Ação humana necessária")).toBeVisible();
    await expect(page.getByText("validacao_clinica")).toBeVisible();

    // Mock the PATCH resolve endpoint to return success, then return empty reviews
    let resolveCallCount = 0;
    await page.route("**/reviews/review-workflow-1/resolve", async (route) => {
      resolveCallCount++;
      await route.fulfill({
        body: JSON.stringify({
          conversationId: mockIds.workflowConversation,
          createdAt: "2026-04-29T03:54:36.000Z",
          id: "review-workflow-1",
          messageId: `${mockIds.workflowConversation}-outbound`,
          metadata: {},
          reason: "validacao_clinica",
          resolvedAt: "2026-04-29T04:00:00.000Z",
          status: "resolved",
        }),
        contentType: "application/json",
        status: 200,
      });
    });

    // After resolve, mock reviews endpoint to return empty
    await page.route("**/reviews", async (route) => {
      if (resolveCallCount > 0) {
        await route.fulfill({
          body: JSON.stringify({ reviewTasks: [] }),
          contentType: "application/json",
          status: 200,
        });
      } else {
        await route.fallback();
      }
    });

    // Click "Aprovar" button
    const approveButton = page.getByTestId("review-approve-review-workflow-1");
    await approveButton.click();

    // Verify the resolve endpoint was called
    expect(resolveCallCount).toBeGreaterThanOrEqual(1);
  });
});
