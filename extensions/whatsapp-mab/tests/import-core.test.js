import test from "node:test";
import assert from "node:assert/strict";
import { apiError, buildImportPayload, conversationUrl, localBaseUrl } from "../import-core.js";

const conversationId = "b4de2205-f0af-49bd-b880-6c9da9a29d15";
const capture = () => ({ captureId: conversationId, chatTitle: "Conversa fictícia", messages: [
  { sourceId: "1", role: "customer", text: "Olá!" },
  { sourceId: "2", role: "attendant", text: "Como posso ajudar?" },
  { sourceId: "3", role: "customer", text: "Vocês aceitam Pix?" },
  { sourceId: "4", role: "attendant", text: "RESPOSTA FUTURA NÃO PODE ENTRAR" },
] });
const choices = { targetSourceId: "3", architectureMode: "centralized_orchestration", runtimeMode: "real" };

test("envia somente o prefixo selecionado preservando papéis e IDs", () => {
  const value = buildImportPayload(capture(), choices);
  assert.deepEqual(value.messages.map((message) => message.sourceId), ["1", "2", "3"]);
  assert.deepEqual(value.messages.map((message) => message.role), ["customer", "attendant", "customer"]);
  assert.ok(!JSON.stringify(value).includes("RESPOSTA FUTURA"));
  assert.equal(value.source, "whatsapp_web");
  assert.equal(value.captureId, conversationId);
  assert.equal(value.runtimeMode, "real");
});

test("exclusão e edição são refletidas no trecho efetivamente enviado", () => {
  const value = capture(); value.messages[0].included = false; value.messages[2].text = " Pergunta revisada ";
  const payload = buildImportPayload(value, choices);
  assert.deepEqual(payload.messages.map((message) => message.sourceId), ["2", "3"]);
  assert.equal(payload.messages.at(-1).text, "Pergunta revisada");
});

test("retry mantém captureId e payload, nova execução depende de novo ID explícito", () => {
  assert.deepEqual(buildImportPayload(capture(), choices), buildImportPayload(capture(), choices));
});

test("não responde a mensagem do atendente ou a mensagem excluída", () => {
  assert.throws(() => buildImportPayload(capture(), { ...choices, targetSourceId: "2" }), /cliente/);
  const value = capture(); value.messages[2].included = false;
  assert.throws(() => buildImportPayload(value, choices), /Selecione a mensagem/);
});

test("participante desconhecido requer correção manual, sem adivinhação", () => {
  const value = capture(); value.messages[0].role = "unknown";
  assert.throws(() => buildImportPayload(value, choices), /quem enviou/);
});

test("valida vazios, limites e IDs duplicados", () => {
  const empty = capture(); empty.messages[1].text = " ";
  assert.throws(() => buildImportPayload(empty, choices), /caracteres/);
  const duplicate = capture(); duplicate.messages[1].sourceId = "1";
  assert.throws(() => buildImportPayload(duplicate, choices), /identificadores/);
  const long = capture(); long.messages[0].text = "x".repeat(8001);
  assert.throws(() => buildImportPayload(long, choices), /8.000/);
});

test("modo simulado e comparação são escolhas explícitas", () => {
  const value = buildImportPayload(capture(), { ...choices, architectureMode: "all_architectures", runtimeMode: "mock" });
  assert.equal(value.architectureMode, "all_architectures"); assert.equal(value.runtimeMode, "mock");
  assert.throws(() => buildImportPayload(capture(), { ...choices, runtimeMode: "auto" }), /modo/);
  assert.throws(() => buildImportPayload(capture(), { ...choices, architectureMode: "new" }), /arquitetura/);
});

test("conexão só aceita loopback HTTP sem credenciais ou caminhos", () => {
  assert.equal(localBaseUrl("http://127.0.0.1:8000/"), "http://127.0.0.1:8000");
  assert.equal(localBaseUrl("http://localhost:3100"), "http://localhost:3100");
  for (const value of ["https://evil.example", "http://127.0.0.1.evil.example", "http://192.168.0.1:8000", "http://user:pass@localhost", "file:///etc/passwd", "http://localhost/path", "http://localhost/?token=a", "http://localhost/#x"]) {
    assert.throws(() => localBaseUrl(value), /use http/);
  }
});

test("abre a conversa correta, sem transportar conteúdo ou credenciais na URL", () => {
  const url = new URL(conversationUrl("http://127.0.0.1:3100", conversationId));
  assert.equal(url.searchParams.get("conversationId"), conversationId);
  assert.equal([...url.searchParams].length, 1);
  assert.throws(() => conversationUrl("http://localhost:3100", "../secret"), /identificador/);
});

test("erros de acesso, conflito e runtime indisponível têm orientação específica", () => {
  assert.match(apiError(401), /chave da API/);
  assert.match(apiError(409), /Nova execução/);
  assert.match(apiError(503), /runtime real/);
});
