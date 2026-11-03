import { expect, test } from "@playwright/test";
import path from "node:path";

const extension = path.resolve(__dirname, "../../../../extensions/whatsapp-mab");
const originalDraft = "Rascunho original preservado";

test("native suggestion editors retain real keyboard focus against WhatsApp capture handlers", async ({ page }) => {
  // This fixture never navigates to WhatsApp or makes an API/model request.
  const fixtureUrl = "https://mab-editor.test/";
  await page.route("**/*", route => route.request().url() === fixtureUrl
    ? route.fulfill({ contentType: "text/html", body: "<!doctype html><html><body></body></html>" })
    : route.abort());
  // An in-memory HTTPS origin supplies the real secure-context crypto API,
  // just like WhatsApp; no request reaches the network or a live browser tab.
  await page.goto(fixtureUrl);
  await page.setContent(`
    <main id="main">
      <header><span title="Contato fictício">Contato fictício</span></header>
      <div data-id="received-question" class="message-in">
        <div aria-label="Contato fictício:"></div>
        <div class="copyable-text" data-pre-plain-text="[10:00] Contato fictício: ">
          <span class="selectable-text">Vocês aceitam Pix?</span>
        </div>
      </div>
      <footer><textarea id="wa-composer" aria-label="Mensagem do WhatsApp">${originalDraft}</textarea></footer>
    </main>
  `);
  await page.evaluate(() => {
    const browser = globalThis as typeof globalThis & {
      chrome: { runtime: { sendMessage: (request: { type: string }) => Promise<unknown> } };
      unexpectedMabRequests: string[];
      focusSteals: number;
    };
    browser.unexpectedMabRequests = [];
    browser.focusSteals = 0;
    browser.chrome = {
      runtime: {
        async sendMessage(request) {
          if (request.type === "mab:settings") {
            return { ok: true, value: { configured: false } };
          }
          browser.unexpectedMabRequests.push(request.type);
          throw new Error("This keyboard regression must not call the MAB API");
        },
      },
    };
    // WhatsApp has document-level keyboard handling. Shadow DOM retargeting
    // makes a textarea look like its non-editable host to a capture listener.
    // Stopping propagation inside that shadow root is then already too late.
    document.addEventListener("keydown", event => {
      const target = event.target;
      if (target instanceof HTMLElement &&
          (target.matches("input, textarea, select") || target.isContentEditable)) return;
      browser.focusSteals++;
      (document.querySelector("#wa-composer") as HTMLTextAreaElement).focus();
    }, true);
  });
  for (const file of ["extractor.js", "panel-core.js", "message-actions.js"]) {
    await page.addScriptTag({ path: path.join(extension, file) });
  }
  await page.evaluate(() => {
    (globalThis as typeof globalThis & {
      MabWhatsAppMessages: { toggle: () => unknown };
    }).MabWhatsAppMessages.toggle();
  });

  // A real Playwright click satisfies the production isTrusted guard.
  await page.getByRole("button", { name: "Sugerir resposta com MAB para esta mensagem" }).click();
  await page.getByText("Ajustar solicitação e conferir contexto", { exact: true }).click();
  const target = page.getByRole("textbox", { name: "Ajustar solicitação", exact: true });
  await expect(target).toHaveValue("Vocês aceitam Pix?");
  await target.click();
  await target.press("ControlOrMeta+A");
  // fill() would bypass the event routing that caused the user-reported bug.
  await target.pressSequentially("Teste de foco");
  await expect(target).toHaveValue("Teste de foco");
  await expect(target).toBeFocused();
  expect(await target.evaluate(element => document.activeElement === element)).toBe(true);
  await expect(page.getByRole("textbox", { name: "Mensagem do WhatsApp", exact: true })).toHaveValue(originalDraft);

  const architecture = page.getByRole("combobox", { name: "Arquitetura", exact: true });
  await architecture.focus();
  // Native select type-ahead avoids OS-specific popup/arrow conventions.
  await architecture.press("w");
  await expect(architecture).toHaveValue("structured_workflow");
  await expect(architecture).toBeFocused();

  const context = page.getByRole("combobox", { name: "Contexto", exact: true });
  await context.focus();
  await context.press("s");
  await expect(context).toHaveValue("target");

  const runtime = page.getByRole("combobox", { name: "Execução", exact: true });
  await runtime.focus();
  await runtime.press("s");
  await expect(runtime).toHaveValue("mock");
  await expect(runtime).toBeFocused();

  await expect(target).toHaveValue("Teste de foco");
  await expect(page.getByRole("textbox", { name: "Mensagem do WhatsApp", exact: true })).toHaveValue(originalDraft);
  expect(await page.evaluate(() => (globalThis as typeof globalThis & { focusSteals: number }).focusSteals)).toBe(0);
  expect(await page.evaluate(() => (globalThis as typeof globalThis & { unexpectedMabRequests: string[] }).unexpectedMabRequests)).toEqual([]);
});
