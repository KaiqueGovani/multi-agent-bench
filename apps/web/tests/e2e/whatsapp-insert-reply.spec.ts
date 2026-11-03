import { expect, test } from "@playwright/test";
import path from "node:path";

const extension = path.resolve(__dirname, "../../../../extensions/whatsapp-mab");
const existingDraft = "Rascunho original preservado";
const workflowReply = "Resposta do Workflow.\nPrimeira linha operacional.\nSegunda linha revisada.";

const scenarios = [
  { name: "an existing draft", text: existingDraft, html: `<p>${existingDraft}</p>`, appended: true, emoji: false },
  { name: "an empty paragraph composer", text: "", html: "<p><br></p>", appended: false, emoji: false },
  { name: "an existing emoji draft", text: "", html: '<p><img id="draft-emoji" alt="🙂" width="16" height="16" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"></p>', appended: true, emoji: true },
];

for (const scenario of scenarios) {
  const initialDraft = scenario.text;
  test(scenario.emoji ? "preserves an emoji-only draft and offers manual copy without sending" : `inserts the selected multiline suggestion into ${scenario.name} without sending`, async ({ page }) => {
  const fixtureUrl = "https://mab-composer.test/";
  await page.route("**/*", route => route.request().url() === fixtureUrl
    ? route.fulfill({ contentType: "text/html", body: "<!doctype html><html><body></body></html>" })
    : route.abort());
  await page.goto(fixtureUrl);
  await page.setContent(`
    <main id="main">
      <header><span title="Contato fictício">Contato fictício</span></header>
      <div data-id="incoming-target" class="message-in">
        <div aria-label="Contato fictício:"></div>
        <div class="copyable-text" data-pre-plain-text="[10:00] Contato fictício: ">
          <span class="selectable-text">Vocês aceitam Pix?</span>
        </div>
      </div>
      <footer>
        <div id="wa-composer" role="textbox" contenteditable="true" data-lexical-editor="true"
          aria-label="Mensagem do WhatsApp" style="white-space:pre-wrap;min-height:80px;border:1px solid #aaa">${scenario.html}</div>
        <button id="wa-send" type="button" aria-label="Enviar mensagem">Enviar</button>
      </footer>
    </main>
  `);
  await page.evaluate(({ reply, draft }) => {
    const fixture = globalThis as typeof globalThis & {
      chrome: { runtime: { sendMessage: (request: { type: string }) => Promise<unknown> } };
      mabFixture: { ready: boolean; calls: string[]; sends: number; inputEvents: number; editorModel: string };
      mabDraftEmoji: Element | null;
    };
    const state: typeof fixture.mabFixture = { ready: false, calls: [], sends: 0, inputEvents: 0, editorModel: draft };
    fixture.mabFixture = state;
    const editor = document.querySelector("#wa-composer") as HTMLElement;
    fixture.mabDraftEmoji = document.querySelector("#draft-emoji");
    editor.addEventListener("input", () => { state.inputEvents++; state.editorModel = editor.innerText; });
    editor.addEventListener("keydown", event => {
      if (event.key === "Enter" && !event.shiftKey) { state.sends++; event.preventDefault(); }
    });
    document.querySelector("#wa-send")!.addEventListener("click", () => { state.sends++; });
    const runIds = ["495dfe9d-e1b1-471b-800d-c8ad0c19931a", "05ab83bb-9e1e-41ce-80c7-e102dc5a8b38", "c40b404d-bdca-467c-b64a-9b472370cc10"];
    const names = ["Centralizada", "Workflow", "Swarm"];
    const replies = ["Resposta da Centralizada.\nOutro texto.", reply, "Resposta do Swarm.\nSugestão diferente."];
    fixture.chrome = { runtime: { async sendMessage(request) {
      state.calls.push(request.type);
      if (request.type === "mab:import") return { ok: true, value: {
        conversationId: "956e4d49-5d34-4938-b735-f1882c40de54", runIds,
      } };
      if (request.type === "mab:progress") return { ok: true, value: {
        runs: runIds.map((id, index) => ({ id, name: names[index], status: state.ready ? "completed" : "running",
          text: state.ready ? replies[index] : "", finished: state.ready })),
        finished: state.ready, ready: state.ready ? 3 : 0,
      } };
      throw new Error(`Unexpected RPC in the insertion fixture: ${request.type}`);
    } } };
  }, { reply: workflowReply, draft: initialDraft });
  for (const file of ["extractor.js", "panel-core.js", "composer.js", "message-actions.js"]) {
    await page.addScriptTag({ path: path.join(extension, file) });
  }
  await page.evaluate(() => (globalThis as typeof globalThis & {
    MabWhatsAppMessages: { toggle: () => unknown };
  }).MabWhatsAppMessages.toggle());

  const row = page.locator("[data-id='incoming-target']");
  const composer = page.getByRole("textbox", { name: "Mensagem do WhatsApp", exact: true });
  await row.getByRole("button", { name: "Sugerir resposta com MAB para esta mensagem" }).click();
  await row.getByRole("combobox", { name: "Arquitetura", exact: true }).selectOption("all_architectures");
  await row.getByRole("button", { name: "Gerar sugestão", exact: true }).click();
  const insert = row.getByRole("button", { name: "Inserir na conversa", exact: true });
  await expect(insert).toBeVisible();
  await expect(insert).toBeDisabled();
  await expect(composer).toHaveText(initialDraft);
  await page.evaluate(() => { (globalThis as typeof globalThis & { mabFixture: { ready: boolean } }).mabFixture.ready = true; });
  await expect(insert).toBeEnabled();
  await expect(row.getByRole("tab")).toHaveCount(3);
  await row.getByRole("tab", { name: "Workflow", exact: true }).click();
  await expect(row.getByRole("tabpanel")).toHaveText(workflowReply);
  await expect(row.getByRole("tab", { name: "Workflow", exact: true })).toHaveAttribute("aria-selected", "true");

  // The operator's trusted click invokes the real contenteditable insertion.
  // No synthetic Enter, send-button click, clipboard or editor-model mock.
  await insert.click();
  const expectedDraft = scenario.appended ? `${initialDraft}\n\n${workflowReply}` : workflowReply;
  if (scenario.emoji) {
    await expect(row.getByRole("status")).toHaveClass(/error/);
    await expect(row.getByRole("status")).toContainText(/copi/i);
    await expect(row.getByRole("button", { name: "Copiar resposta", exact: true })).toBeEnabled();
    await expect(composer.locator("#draft-emoji")).toHaveCount(1);
    await expect(composer.locator("#draft-emoji")).toHaveAttribute("alt", "🙂");
    expect(await page.evaluate(() => document.querySelector("#draft-emoji") ===
      (globalThis as typeof globalThis & { mabDraftEmoji: Element | null }).mabDraftEmoji)).toBe(true);
    expect(await composer.innerText()).toBe(initialDraft);
  } else {
    await expect.poll(() => composer.innerText()).toBe(expectedDraft);
    await expect(composer).toBeFocused();
    await expect(row.getByRole("status")).toContainText(scenario.appended ? "Sugestão acrescentada ao rascunho existente." : "Sugestão inserida na caixa de mensagem.");
  }
  const insertedState = await page.evaluate(() => (globalThis as typeof globalThis & {
    mabFixture: { sends: number; inputEvents: number; editorModel: string; calls: string[] };
  }).mabFixture);
  expect(insertedState.editorModel).toBe(scenario.emoji ? initialDraft : expectedDraft);
  if (scenario.emoji) expect(insertedState.inputEvents).toBe(0);
  else expect(insertedState.inputEvents).toBeGreaterThan(0);
  expect(insertedState.sends).toBe(0);
  expect(insertedState.calls.filter(type => type === "mab:import")).toHaveLength(1);
  expect(await composer.innerText()).not.toContain("Resposta da Centralizada");
  expect(await composer.innerText()).not.toContain("Resposta do Swarm");

  // Emulate opening another chat: the old card must disappear and its draft
  // insertion guard must also refuse work even if called with a stale handle.
  await page.evaluate(() => {
    const title = document.querySelector("#main header span")!;
    title.textContent = "Outro contato fictício";
    title.setAttribute("title", "Outro contato fictício");
    const editor = document.querySelector("#wa-composer") as HTMLElement;
    editor.setAttribute("aria-label", "Mensagem da nova conversa");
    editor.textContent = "Rascunho da nova conversa";
  });
  await expect(insert).toHaveCount(0);
  const stale = await page.evaluate(() => {
    const fixture = globalThis as typeof globalThis & {
      MabWhatsAppComposer: { insertReply: (options: { main: Element; isCurrent: () => boolean; text: string }) => unknown };
      mabFixture: { sends: number; inputEvents: number };
    };
    const before = fixture.mabFixture.inputEvents;
    let refused = false;
    try {
      fixture.MabWhatsAppComposer.insertReply({ main: document.querySelector("#main")!, isCurrent: () => false, text: "NÃO INSERIR NA NOVA CONVERSA" });
    } catch { refused = true; }
    return { refused, before, after: fixture.mabFixture.inputEvents, sends: fixture.mabFixture.sends };
  });
  expect(stale.refused).toBe(true);
  expect(stale.after).toBe(stale.before);
  expect(stale.sends).toBe(0);
  await expect(page.getByRole("textbox", { name: "Mensagem da nova conversa", exact: true })).toHaveText("Rascunho da nova conversa");
});
}
