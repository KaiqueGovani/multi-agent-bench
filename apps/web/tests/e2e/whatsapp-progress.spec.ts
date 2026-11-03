import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const extension = path.resolve(__dirname, "../../../../extensions/whatsapp-mab");
const runIds = ["ae599d40-a026-4fce-a513-bbc843569f50", "cce254bf-fe48-4d52-9b8f-aa8599b99e2f", "2620f927-7900-415b-b3c1-f86d9f08a741"];
const names = ["Centralizada", "Workflow", "Swarm"];
const architectures = ["centralized_orchestration", "structured_workflow", "decentralized_swarm"];
const imported = { conversationId: "f031f0f2-924b-4d25-a0b1-bac908775324", runIds };
type Request = { type: string; conversationId?: string; runIds?: string[] };
type Pending = { request: Request; resolve: (reply: unknown) => void; reject: (error: Error) => void };

function progress(statuses: string[]) {
  return {
    runs: statuses.map((status, index) => ({
      id: runIds[index], name: names[index], architecture: architectures[index], status,
      finished: ["completed", "failed", "cancelled", "human_review_required"].includes(status),
      text: status === "completed" ? `Resposta fictícia da ${names[index]}.` : "",
      error: status === "failed" ? "Falha fictícia do provedor" : null,
    })),
    finished: statuses.every(status => ["completed", "failed", "cancelled", "human_review_required"].includes(status)),
    ready: statuses.filter(status => status === "completed").length,
  };
}

async function setup(page: Page) {
  // Only an in-memory HTTPS document and test RPC promises are involved.
  const url = "https://mab-progress.test/";
  await page.route("**/*", route => route.request().url() === url
    ? route.fulfill({ contentType: "text/html", body: "<!doctype html><html><body></body></html>" })
    : route.abort());
  await page.clock.install();
  await page.goto(url);
  await page.setContent(`
    <style>
      body{margin:0;padding:18px;background:#eae6df;font:14px/1.4 system-ui;color:#233138}
      #main{max-width:650px;margin:auto;background:#efeae2;border:1px solid #d6d9d5}
      header,footer{padding:12px 16px;background:#f0f2f5}
      [data-id]{padding:8px 12px}.copyable-text{display:table;max-width:85%;padding:7px 10px;border-radius:6px;background:white}
      .message-out>.copyable-text{margin-left:auto;background:#d9fdd3}
      footer [contenteditable]{min-height:30px;white-space:pre-wrap;padding:8px;background:white;border-radius:6px}
    </style>
    <main id="main"><header><span title="Contato fictício">Contato fictício</span></header>
      <div class="message-out" data-id="attendant-context"><div aria-label="Você:"></div><div class="copyable-text" data-pre-plain-text="[10:00] Você: "><span class="selectable-text">Como podemos ajudar?</span></div></div>
      <div class="message-in" data-id="target"><div aria-label="Contato fictício:"></div><div class="copyable-text" data-pre-plain-text="[10:01] Contato fictício: "><span class="selectable-text">Vocês aceitam Pix?</span></div></div>
      <footer><div contenteditable="true" role="textbox" aria-label="Mensagem do WhatsApp">Rascunho preservado</div></footer>
    </main>
  `);
  const pending: Pending[] = [];
  await page.exposeFunction("mabTestRpc", (request: Request) => new Promise((resolve, reject) => {
    pending.push({ request, resolve, reject });
  }));
  await page.evaluate(() => {
    const fixture = globalThis as typeof globalThis & {
      chrome: { runtime: { sendMessage: (request: unknown) => Promise<unknown> } };
      mabTestRpc: (request: unknown) => Promise<unknown>;
    };
    fixture.chrome = { runtime: { sendMessage: request => fixture.mabTestRpc(request) } };
  });
  for (const file of ["extractor.js", "panel-core.js", "composer.js", "message-actions.js"]) {
    await page.addScriptTag({ path: path.join(extension, file) });
  }
  await page.evaluate(() => (globalThis as typeof globalThis & {
    MabWhatsAppMessages: { toggle: () => unknown };
  }).MabWhatsAppMessages.toggle());
  const row = page.locator("[data-id='target']");
  const card = row.getByRole("region", { name: "Sugestão MAB para esta mensagem", exact: true });
  const action = () => row.getByRole("button", { name: "Sugerir resposta com MAB para esta mensagem", exact: true });
  await action().click();
  await row.getByRole("combobox", { name: "Arquitetura", exact: true }).selectOption("all_architectures");
  async function call(type: string, index = 0) {
    await expect.poll(() => pending.filter(item => item.request.type === type).length).toBeGreaterThan(index);
    return pending.filter(item => item.request.type === type)[index];
  }
  return { row, card, action, pending, call, progress: card.locator("#progress") };
}

test("shows sending, queued and partial architecture progress, then reports a terminal failure accurately", async ({ page }) => {
  const fixture = await setup(page);
  await fixture.card.getByRole("button", { name: "Gerar sugestão", exact: true }).click();
  const sending = await fixture.call("mab:import");
  await expect(fixture.progress).toBeVisible();
  await expect(fixture.progress).toHaveAttribute("aria-label", "Progresso da sugestão");
  await expect(fixture.progress).toHaveAttribute("data-phase", "sending");
  await expect(fixture.progress.locator("#progress-title")).toHaveText("Enviando trecho");
  await expect(fixture.progress.locator(".progress-spinner")).toBeVisible();
  await expect(fixture.card.locator("#generate")).toHaveAttribute("aria-busy", "true");
  // Progress announcements and completed partial responses must remain outside
  // the busy subtree, so assistive technology can announce them immediately.
  expect(await fixture.card.getAttribute("aria-busy")).toBeNull();
  await expect(fixture.card.getByRole("button", { name: "Gerando sugestão…", exact: true })).toBeDisabled();
  expect(fixture.pending.filter(item => item.request.type === "mab:import")).toHaveLength(1);

  sending.resolve({ ok: true, value: imported });
  (await fixture.call("mab:progress")).resolve({ ok: true, value: progress(["pending", "pending", "pending"]) });
  await expect(fixture.progress).toHaveAttribute("data-phase", "running");
  await expect(fixture.progress.locator("#progress-title")).toHaveText("Processando no MAB");
  await expect(fixture.progress.locator("#progress-runs li")).toHaveCount(3);
  for (const id of runIds) await expect(fixture.progress.locator(`[data-run-id='${id}']`)).toContainText("Na fila");

  await page.clock.runFor(1850);
  (await fixture.call("mab:progress", 1)).resolve({ ok: true, value: progress(["completed", "running", "pending"]) });
  await expect(fixture.progress.locator("#progress-summary")).toContainText("1 de 3 finalizadas");
  await expect(fixture.progress.locator(`[data-run-id='${runIds[0]}']`)).toContainText("Concluída");
  await expect(fixture.progress.locator(`[data-run-id='${runIds[1]}']`)).toContainText("Em execução");
  await expect(fixture.progress.locator(`[data-run-id='${runIds[2]}']`)).toContainText("Na fila");
  await expect(fixture.card.locator("#generate")).toHaveAttribute("aria-busy", "true");
  const screenshot = path.resolve(__dirname, "../../../../var/whatsapp-demo/progress-preview.png");
  await fs.mkdir(path.dirname(screenshot), { recursive: true });
  await page.locator("#main").screenshot({ path: screenshot });

  await page.clock.runFor(1850);
  (await fixture.call("mab:progress", 2)).resolve({ ok: true, value: progress(["completed", "completed", "failed"]) });
  await expect(fixture.progress).toHaveAttribute("data-phase", "complete");
  await expect(fixture.progress.locator("#progress-title")).toHaveText("Processamento encerrado");
  await expect(fixture.progress.locator("#progress-summary")).toContainText("3 de 3 finalizadas");
  await expect(fixture.progress.locator(`[data-run-id='${runIds[2]}']`)).toContainText("Falhou");
  await expect(fixture.card.locator("#generate")).toHaveAttribute("aria-busy", "false");
  await expect(fixture.progress.locator(".progress-spinner")).toBeHidden();
  await fixture.card.getByRole("tab", { name: "Swarm", exact: true }).click();
  await expect(fixture.card.getByRole("tabpanel")).toHaveText("Falha fictícia do provedor");
  await expect(fixture.card.getByRole("button", { name: "Inserir na conversa", exact: true })).toBeDisabled();
  await expect(fixture.card.getByRole("button", { name: "Copiar resposta", exact: true })).toBeDisabled();
});

test("stops busy feedback after a polling error or timeout and retries existing runs without importing twice", async ({ page }) => {
  const fixture = await setup(page);
  await fixture.card.getByRole("button", { name: "Gerar sugestão", exact: true }).click();
  (await fixture.call("mab:import")).resolve({ ok: true, value: imported });
  (await fixture.call("mab:progress")).reject(new Error("Conexão fictícia interrompida"));
  await expect(fixture.progress).toHaveAttribute("data-phase", "error");
  await expect(fixture.progress.locator("#progress-title")).toHaveText("Não foi possível atualizar");
  await expect(fixture.progress.locator("#progress-summary")).toContainText("Sem confirmação de execução");
  await expect(fixture.progress.locator("#progress-summary")).not.toContainText("Último estado recebido");
  await expect(fixture.card.locator("#status")).toContainText("Conexão fictícia interrompida");
  await expect(fixture.card.locator("#generate")).toHaveAttribute("aria-busy", "false");
  await expect(fixture.progress.locator(".progress-spinner")).toBeHidden();
  await fixture.card.getByRole("button", { name: "Atualizar resposta", exact: true }).click();
  const retry = await fixture.call("mab:progress", 1);
  await expect(fixture.card.locator("#generate")).toHaveAttribute("aria-busy", "true");
  await expect(fixture.progress.locator(".progress-spinner")).toBeVisible();
  // Advance elapsed time while the RPC is unresolved; no real waiting needed.
  await page.clock.fastForward(181000);
  retry.resolve({ ok: true, value: progress(["running", "pending", "pending"]) });
  await expect(fixture.progress).toHaveAttribute("data-phase", "paused");
  await expect(fixture.progress.locator("#progress-title")).toHaveText("Acompanhamento pausado");
  await expect(fixture.card.locator("#generate")).toHaveAttribute("aria-busy", "false");
  await expect(fixture.progress.locator(".progress-spinner")).toBeHidden();
  await fixture.card.getByRole("button", { name: "Atualizar resposta", exact: true }).click();
  (await fixture.call("mab:progress", 2)).resolve({ ok: true, value: progress(["completed", "completed", "completed"]) });
  await expect(fixture.progress).toHaveAttribute("data-phase", "complete");
  await expect(fixture.progress.locator("#progress-title")).toHaveText("Respostas disponíveis");
  const beforeClose = fixture.pending.length;
  await fixture.card.getByRole("button", { name: "Fechar sugestão", exact: true }).click();
  await expect(fixture.card).toHaveCount(0);
  await fixture.action().click();
  await expect(fixture.progress).toHaveAttribute("data-phase", "complete");
  await expect(fixture.card.getByRole("tabpanel")).toHaveText("Resposta fictícia da Centralizada.");
  expect(fixture.pending).toHaveLength(beforeClose);
  expect(fixture.pending.filter(item => item.request.type === "mab:import")).toHaveLength(1);
});

test("discards a late import result after switching chats while the new suggestion keeps its own progress", async ({ page }) => {
  const fixture = await setup(page);
  await fixture.card.getByRole("button", { name: "Gerar sugestão", exact: true }).click();
  const oldImport = await fixture.call("mab:import");
  await expect(fixture.progress).toHaveAttribute("data-phase", "sending");
  await page.evaluate(() => {
    const title = document.querySelector("#main header span")!;
    title.textContent = "Outro contato fictício";
    title.setAttribute("title", "Outro contato fictício");
    document.querySelector("#main footer [contenteditable]")!.setAttribute("aria-label", "Mensagem da nova conversa");
  });
  await expect(fixture.card).toHaveCount(0);
  await page.clock.runFor(80);
  await fixture.action().click();
  await fixture.card.getByRole("button", { name: "Gerar sugestão", exact: true }).click();
  const newImport = await fixture.call("mab:import", 1);
  oldImport.resolve({ ok: true, value: imported });
  await expect(fixture.progress).toHaveAttribute("data-phase", "sending");
  expect(fixture.pending.filter(item => item.request.type === "mab:progress")).toHaveLength(0);
  const currentImport = { conversationId: "1f058a9b-e753-4ccc-a682-bf72b12cf0ca", runIds };
  newImport.resolve({ ok: true, value: currentImport });
  const currentPoll = await fixture.call("mab:progress");
  expect(currentPoll.request.conversationId).toBe(currentImport.conversationId);
  currentPoll.resolve({ ok: true, value: progress(["completed", "completed", "completed"]) });
  await expect(fixture.progress).toHaveAttribute("data-phase", "complete");
  await expect(fixture.card.getByRole("tabpanel")).toHaveText("Resposta fictícia da Centralizada.");
  expect(fixture.pending.filter(item => item.request.type === "mab:import")).toHaveLength(2);
  expect(fixture.pending.filter(item => item.request.type === "mab:progress")).toHaveLength(1);
  await expect(page.getByRole("textbox", { name: "Mensagem da nova conversa", exact: true })).toHaveText("Rascunho preservado");
});
