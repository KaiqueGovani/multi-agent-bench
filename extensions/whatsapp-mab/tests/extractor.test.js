import test from "node:test";
import assert from "node:assert/strict";
import { parseHTML } from "linkedom";
import "../extractor.js";

const capture = (body) => globalThis.MabWhatsAppCapture.captureWhatsApp(parseHTML(`<html><body>${body}</body></html>`).document);
const message = (id, sender, text) => `<div data-id="${id}" data-testid="conv-msg-${id}"><div aria-label="${sender}:"></div><div class="copyable-text" data-pre-plain-text="[15:04, 31/10/2026] ${sender}: "><span class="selectable-text copyable-text">${text}</span></div></div>`;

test("DOM atual com IDs opacos identifica Você e participante pelo rótulo acessível", () => {
  const result = capture(`<aside>${message("other", "Conversa fictícia", "Não capturar lista lateral")}</aside><div id="main"><header>Conversa fictícia</header>${message("a1b2c3", "Conversa fictícia", "Vocês aceitam Pix?")}${message("d4e5f6", "Você", "Vou conferir.")}</div>`);
  assert.equal(result.chatTitle, "Conversa fictícia");
  assert.deepEqual(result.messages.map(({ sourceId, role, text }) => ({ sourceId, role, text })), [
    { sourceId: "a1b2c3", role: "customer", text: "Vocês aceitam Pix?" },
    { sourceId: "d4e5f6", role: "attendant", text: "Vou conferir." },
  ]);
  assert.equal(result.historyScope, "rendered_only");
  assert.equal(result.messages[0].displayTimestamp, "15:04, 31/10/2026");
  assert.equal(result.messages[0].timestamp, undefined, "não inventa timezone ou UTC");
});

test("layouts antigos continuam aceitos com classes de direção", () => {
  const result = capture(`<div id="main"><header><span title="Teste">Teste</span></header><div data-id="opaque"><div class="message-in"><div data-pre-plain-text=""><span class="selectable-text">Olá</span></div></div></div></div>`);
  assert.equal(result.messages[0].role, "customer");
});

test("sender não reconhecido permanece desconhecido para revisão", () => {
  const result = capture(`<div id="main"><header>Conversa fictícia</header>${message("opaque", "Outra pessoa", "Não adivinhar")}</div>`);
  assert.equal(result.messages[0].role, "unknown");
});

test("citação não duplica o texto da mensagem, reação e horário não entram", () => {
  const result = capture(`<div id="main"><header>Conversa fictícia</header><div data-id="opaque"><div aria-label="Você:"></div><div data-pre-plain-text="[15:04] Você: "><div data-testid="quoted-message"><span class="selectable-text">Texto antigo citado</span></div><span class="selectable-text">Texto atual</span><span data-icon="msg-check"></span><span>15:04</span></div></div></div>`);
  assert.equal(result.messages[0].text, "Texto atual");
});

test("anexo sem texto vira descritor explícito, sem inferir conteúdo", () => {
  const result = capture(`<div id="main"><header>Conversa fictícia</header><div data-id="image"><div aria-label="Conversa fictícia:"></div><img src="blob:fake"></div></div>`);
  assert.match(result.messages[0].text, /Conteúdo não capturado/);
});

test("ignora itens ocultos, placeholders e duplica apenas uma vez cada ID", () => {
  const result = capture(`<div id="main"><header>Conversa fictícia</header><div aria-hidden="true">${message("hidden", "Conversa fictícia", "Oculto")}</div><div data-id="placeholder"></div>${message("same", "Conversa fictícia", "Uma vez")}${message("same", "Conversa fictícia", "Uma vez")}</div>`);
  assert.equal(result.messages.length, 1); assert.equal(result.messages[0].text, "Uma vez");
});

test("sem conversa aberta ou sem mensagens fornece erro recuperável", () => {
  assert.throws(() => capture("<div>WhatsApp</div>"), /Abra uma conversa/);
  assert.throws(() => capture('<div id="main"><header>Conversa fictícia</header></div>'), /Não encontrei mensagens/);
});
