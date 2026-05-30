import { expect, test } from "@playwright/test";

import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

test("keeps chat as the main surface and moves technical monitoring to dashboard", async ({ page }) => {
  await installMockEventSource(page);
  await mockFrontendApi(page);

  await page.goto("/");

  await expect(page.getByText("Nenhuma conversa ativa")).toBeVisible();
  await expect(page.getByTestId("message-list-empty")).toContainText("Nenhuma mensagem ainda");

  await page.goto(`/?conversationId=${mockIds.swarmConversation}`);

  await expect(page).toHaveURL(new RegExp(`conversationId=${mockIds.swarmConversation}`));
  await expect(page.getByTestId("message-list")).toContainText("Tem dipirona em estoque?");
  await expect(page.getByTestId("message-list")).toContainText("O estoque foi confirmado pelo fluxo swarm.");
  await expect(page.getByText("Arquitetura travada para esta conversa")).toBeVisible();
  await expect(page.getByTestId("architecture-select")).toBeDisabled();
  await expect(page.getByTestId("runtime-visual-swarm")).toHaveCount(0);

  await page.getByTestId("dashboard-link").click();

  await expect(page).toHaveURL(new RegExp(`/dashboard\\?conversationId=${mockIds.swarmConversation}$`));
  await expect(page.getByTestId("dashboard-page")).toBeVisible();
  await expect(page.getByTestId("runtime-panel-technical")).toBeVisible();
  await expect(page.getByText("Monitor técnico do runtime")).toBeVisible();
});

test("renders markdown in received chat messages", async ({ page }) => {
  await installMockEventSource(page);
  await mockFrontendApi(page);

  await page.goto(`/?conversationId=${mockIds.centralizedConversation}`);

  const outboundMessage = page.getByTestId(`message-${mockIds.centralizedConversation}-outbound`);
  await expect(outboundMessage.locator("strong")).toHaveText("dipirona 500 mg");
  await expect(outboundMessage.locator("li")).toHaveText(["Estoque confirmado", "Retirada no balcão"]);
  await expect(outboundMessage.locator("a")).toHaveAttribute("href", "https://example.com/produto/dipirona");
});

test("renders overview responses as collapsed markdown", async ({ page }) => {
  await installMockEventSource(page);
  await mockFrontendApi(page);

  await page.goto(`/?conversationId=${mockIds.centralizedConversation}`);
  await page.getByRole("button", { name: "Visão Geral" }).click();

  const responseDisclosure = page.getByTestId("overview-response");
  await expect(responseDisclosure).not.toHaveAttribute("open", "");

  await responseDisclosure.locator("summary").click();

  await expect(responseDisclosure).toHaveAttribute("open", "");
  await expect(responseDisclosure.locator("strong")).toHaveText("dipirona 500 mg");
  await expect(responseDisclosure.locator("li")).toHaveText(["Estoque confirmado", "Retirada no balcão"]);
  await expect(responseDisclosure.locator("a")).toHaveAttribute("href", "https://example.com/produto/dipirona");
});

test("starts a local draft and creates the backend conversation only on first send", async ({ page }) => {
  await installMockEventSource(page);
  await mockFrontendApi(page);
  const conversationCreateRequests: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/conversations")) {
      conversationCreateRequests.push(request.url());
    }
  });

  await page.goto(`/?conversationId=${mockIds.swarmConversation}`);
  await expect(page.getByTestId("message-list")).toContainText("Tem dipirona em estoque?");

  await page.getByRole("button", { name: "Nova conversa" }).click();

  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByText("Nenhuma conversa ativa")).toBeVisible();
  await expect(page.getByTestId("message-list-empty")).toContainText("Nenhuma mensagem ainda");
  await expect(page.getByTestId("architecture-select")).toBeEnabled();
  expect(conversationCreateRequests).toHaveLength(0);

  const createRequest = page.waitForRequest((request) => (
    request.method() === "POST" && request.url().endsWith("/conversations")
  ));
  await page.getByTestId("message-composer-input").fill("Nova mensagem de teste");
  await page.getByRole("button", { name: "Enviar" }).click();
  await createRequest;

  await expect(page).toHaveURL(new RegExp(`conversationId=${mockIds.draftConversation}`));
  await expect(page.getByTestId("message-list")).toContainText("Nova mensagem de teste");
});
