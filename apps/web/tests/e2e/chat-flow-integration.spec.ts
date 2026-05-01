import { expect, test } from "@playwright/test";

import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

test("complete chat flow: open app, select architecture, send message, receive response", async ({ page }) => {
  await installMockEventSource(page);

  await mockFrontendApi(page);

  // Bridge localhost → 127.0.0.1 so mockFrontendApi intercepts regardless of env config
  await page.route("http://localhost:8000/**", (route) =>
    route.fallback({ url: route.request().url().replace("http://localhost:8000", "http://127.0.0.1:8000") }),
  );

  // Track API calls
  const postConversationRequests: Array<{ url: string; body: string }> = [];
  const postMessageRequests: Array<{ url: string; body: string }> = [];

  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/conversations")) {
      postConversationRequests.push({ url: request.url(), body: request.postData() ?? "" });
    }
    if (request.method() === "POST" && request.url().endsWith("/messages")) {
      postMessageRequests.push({ url: request.url(), body: request.postData() ?? "" });
    }
  });

  // 1. Open app — empty state is shown
  await page.goto("/");
  await expect(page.getByTestId("message-list-empty")).toContainText("Nenhuma mensagem ainda");
  await expect(page.getByText("Nenhuma conversa ativa")).toBeVisible();

  // 2. Architecture dropdown is enabled and can be selected
  const architectureSelect = page.getByTestId("architecture-select");
  await expect(architectureSelect).toBeEnabled();
  await architectureSelect.selectOption("centralized_orchestration");
  await expect(architectureSelect).toHaveValue("centralized_orchestration");

  // 3. Type a message
  const messageInput = page.getByTestId("message-composer-input");
  await messageInput.fill("Nova mensagem de teste");
  await expect(messageInput).toHaveValue("Nova mensagem de teste");

  // 4. Submit the message — wait for both POST /conversations and POST /messages
  const conversationCreatePromise = page.waitForRequest(
    (req) => req.method() === "POST" && req.url().endsWith("/conversations"),
  );
  const messageCreatePromise = page.waitForRequest(
    (req) => req.method() === "POST" && req.url().endsWith("/messages"),
  );

  await page.locator("form button[type='submit']").click();

  await conversationCreatePromise;
  await messageCreatePromise;

  // 5. Verify POST /conversations was called (lazy creation)
  expect(postConversationRequests).toHaveLength(1);

  // 6. Verify POST /messages was called with correct data
  expect(postMessageRequests).toHaveLength(1);

  // 7. URL updates to include the new conversation ID
  await expect(page).toHaveURL(new RegExp(`conversationId=${mockIds.draftConversation}`));

  // 8. User message appears in the message list
  await expect(page.getByTestId("message-list")).toContainText("Nova mensagem de teste");

  // 9. Bot response appears (from GET /conversations/{id} mock which returns outbound message)
  await expect(page.getByTestId("message-list")).toContainText("Processando a nova conversa.");

  // 10. Both messages are rendered as articles
  const messages = page.locator("article[data-testid^='message-']");
  await expect(messages).toHaveCount(2);

  // 11. Architecture dropdown is disabled after first send
  await expect(architectureSelect).toBeDisabled();
});
