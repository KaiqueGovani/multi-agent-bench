import { expect, test } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const extension = path.resolve(__dirname, "../../../../extensions/whatsapp-mab");
const preview = path.resolve(__dirname, "../../../../var/whatsapp-demo/context-markers-preview.png");
const targetId = "message-12";
const recentIds = Array.from({ length: 10 }, (_, index) => `message-${index + 3}`);

type CapturedMessage = { sourceId: string; role: string; text: string };
type ImportCall = {
  type: string;
  capture: { messages: CapturedMessage[] };
  choices: { targetSourceId: string; architectureMode: string; runtimeMode: string };
};

test("context markers match the exact imported prefix for both customer and attendant messages", async ({ page }) => {
  await page.setViewportSize({ width: 1100, height: 1000 });
  // HTTPS is supplied entirely in memory so crypto.randomUUID is native.
  // Neither WhatsApp, the MAB API nor a model provider receives any request.
  const fixtureUrl = "https://mab-context.test/";
  await page.route("**/*", route => route.request().url() === fixtureUrl
    ? route.fulfill({ contentType: "text/html", body: "<!doctype html><html><body></body></html>" })
    : route.abort());
  await page.goto(fixtureUrl);
  const messages = Array.from({ length: 15 }, (_, index) => {
    const incoming = index % 2 === 0;
    const sender = incoming ? "Contato fictício" : "Você";
    const text = index === 12 ? "Vocês aceitam Pix?" : index > 12
      ? `Mensagem posterior ${index} · fora do trecho escolhido`
      : `${incoming ? "Cliente" : "Atendente"} · mensagem de teste ${index}`;
    return `<div data-id="message-${index}" class="${incoming ? "message-in" : "message-out"}">
      <div aria-label="${sender}:"></div>
      <div class="copyable-text" data-pre-plain-text="[10:00] ${sender}: "><span class="selectable-text">${text}</span></div>
    </div>`;
  });
  await page.setContent(`
    <style>
      body{margin:0;padding:16px;background:#eae6df;font:14px/1.4 system-ui,sans-serif;color:#233138}
      #main{max-width:920px;margin:auto;background:#efeae2;border:1px solid #d6d9d5}
      header{padding:14px 20px;background:#f0f2f5;border-bottom:1px solid #d6d9d5;font-weight:600}
      [data-id]{padding:3px 14px;clear:both;min-height:32px}
      .copyable-text{max-width:60%;display:table;padding:6px 12px;border-radius:6px;background:white}
      .message-out>.copyable-text{margin-left:auto;background:#d9fdd3}
      footer{padding:10px 18px;background:#f0f2f5;clear:both}footer textarea{box-sizing:border-box;width:100%;font:inherit;padding:7px;border:1px solid #ccd0d5;border-radius:6px}
    </style>
    <main id="main"><header><span title="Contato fictício">Contato fictício</span></header>
      ${messages.join("")}
      <footer><textarea aria-label="Mensagem do WhatsApp">Rascunho original preservado</textarea></footer>
    </main>
  `);
  await page.evaluate(() => {
    const fixture = globalThis as typeof globalThis & {
      chrome: { runtime: { sendMessage: (request: { type: string }) => Promise<unknown> } };
      mabFixtureCalls: unknown[];
    };
    fixture.mabFixtureCalls = [];
    const runId = "12c56f76-a2d4-41d1-a6ab-1b1da3ae0bda";
    fixture.chrome = { runtime: { async sendMessage(request) {
      fixture.mabFixtureCalls.push(structuredClone(request));
      if (request.type === "mab:import") return { ok: true, value: {
        conversationId: "092348c5-ebad-4319-b835-ff94f37552b7", runIds: [runId],
      } };
      if (request.type === "mab:progress") return { ok: true, value: {
        runs: [{ id: runId, name: "Centralizada", text: "Resposta fictícia para o teste local.", finished: true }],
        finished: true, ready: 1,
      } };
      throw new Error(`Unexpected RPC in the marker fixture: ${request.type}`);
    } } };
  });
  for (const file of ["extractor.js", "panel-core.js", "message-actions.js"]) {
    await page.addScriptTag({ path: path.join(extension, file) });
  }
  await page.evaluate(() => (globalThis as typeof globalThis & {
    MabWhatsAppMessages: { toggle: () => unknown };
  }).MabWhatsAppMessages.toggle());

  const markers = page.locator("[data-mab-ui='context-marker']");
  const markerIds = () => markers.evaluateAll(nodes => nodes.map(node => node.getAttribute("data-mab-source")));
  const imports = () => page.evaluate(() => (globalThis as typeof globalThis & {
    mabFixtureCalls: ImportCall[];
  }).mabFixtureCalls.filter(request => request.type === "mab:import"));
  const row = page.locator(`[data-id='${targetId}']`);
  await expect(markers).toHaveCount(0);
  await row.getByRole("button", { name: "Sugerir resposta com MAB para esta mensagem" }).click();
  await expect(markers).toHaveCount(10);
  expect(await markerIds()).toEqual(recentIds);
  await expect(page.locator(".message-out > [data-mab-ui='context-marker']")).toHaveCount(5);
  await expect(page.locator(".message-in > [data-mab-ui='context-marker']")).toHaveCount(5);
  await expect(row.locator("[data-mab-context='target']")).toHaveCount(1);
  await expect(page.locator("[data-id='message-13'] [data-mab-ui='context-marker']")).toHaveCount(0);
  await expect(page.locator("[data-id='message-14'] [data-mab-ui='context-marker']")).toHaveCount(0);
  await expect(row.getByText("✓ Solicitação selecionada", { exact: true })).toBeVisible();
  expect(await imports()).toEqual([]);
  await fs.mkdir(path.dirname(preview), { recursive: true });
  await page.screenshot({ path: preview, fullPage: true });

  await row.getByText("Ajustar solicitação e conferir contexto", { exact: true }).click();
  const editor = row.getByRole("textbox", { name: "Ajustar solicitação", exact: true });
  await editor.click();
  await editor.press("ControlOrMeta+A");
  await editor.pressSequentially("Solicitação revisada no teste");
  await expect(editor).toBeFocused();
  await expect(row.getByText("✓ Solicitação selecionada · Texto ajustado no MAB", { exact: true })).toBeVisible();
  await expect(row.locator(".selectable-text")).toHaveText("Vocês aceitam Pix?");
  expect(await markerIds()).toEqual(recentIds);
  const recaptured = await page.evaluate(() => (globalThis as typeof globalThis & {
    MabWhatsAppCapture: { captureWhatsApp: () => { messages: CapturedMessage[] } };
  }).MabWhatsAppCapture.captureWhatsApp());
  expect(recaptured.messages).toHaveLength(15);
  expect(recaptured.messages.find(message => message.sourceId === targetId)?.text).toBe("Vocês aceitam Pix?");
  expect(JSON.stringify(recaptured.messages)).not.toContain("Será enviada");
  expect(JSON.stringify(recaptured.messages)).not.toContain("Solicitação selecionada");
  expect(JSON.stringify(recaptured.messages)).not.toContain("Solicitação revisada");

  // Use the actual background payload builder, rather than mirroring its logic.
  const { buildImportPayload } = await import(pathToFileURL(path.join(extension, "import-core.js")).href);
  await row.getByRole("button", { name: "Gerar sugestão", exact: true }).click();
  await expect.poll(async () => (await imports()).length).toBe(1);
  await expect(row.getByText("Resposta fictícia para o teste local.", { exact: true })).toBeVisible();
  const first = (await imports())[0];
  const recentPayload = buildImportPayload(first.capture, first.choices);
  expect(recentPayload.messages.map((message: CapturedMessage) => message.sourceId)).toEqual(await markerIds());
  expect(recentPayload.messages.filter((message: CapturedMessage) => message.role === "attendant")).toHaveLength(5);
  expect(recentPayload.messages.at(-1).text).toBe("Solicitação revisada no teste");
  expect(JSON.stringify(recentPayload)).not.toContain("Mensagem posterior");

  await row.getByRole("button", { name: "Nova sugestão", exact: true }).click();
  await row.getByRole("combobox", { name: "Contexto", exact: true }).selectOption("target");
  await expect(markers).toHaveCount(1);
  expect(await markerIds()).toEqual([targetId]);
  await row.getByRole("button", { name: "Gerar sugestão", exact: true }).click();
  await expect.poll(async () => (await imports()).length).toBe(2);
  await expect(row.getByText("Resposta fictícia para o teste local.", { exact: true })).toBeVisible();
  const second = (await imports())[1];
  const targetPayload = buildImportPayload(second.capture, second.choices);
  expect(targetPayload.messages.map((message: CapturedMessage) => message.sourceId)).toEqual(await markerIds());
  expect(targetPayload.messages[0].text).toBe("Solicitação revisada no teste");
  expect(targetPayload.captureId).not.toBe(recentPayload.captureId);
  await row.getByRole("button", { name: "Fechar sugestão", exact: true }).click();
  await expect(markers).toHaveCount(0);
  await expect(page.getByRole("textbox", { name: "Mensagem do WhatsApp", exact: true })).toHaveValue("Rascunho original preservado");
});
