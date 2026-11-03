import { apiError, buildImportPayload, conversationUrl, localBaseUrl } from "./import-core.js";

const $ = (id) => document.getElementById(id);
const originalId = new URL(location.href).searchParams.get("capture");
let capture;
let selectedTarget;
let imported;
let submittedPayload;
const settings = { apiBase: "http://127.0.0.1:8000", webBase: "http://127.0.0.1:3100", apiKey: "" };

function announce(text, error = false) {
  const box = $(error ? "error" : "status");
  box.textContent = text;
  box.hidden = !text;
  $(error ? "status" : "error").hidden = true;
  if (error) box.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function saveDraft() {
  // Never use sync storage for messages or keys; session data expires with Chrome.
  if (capture) await chrome.storage.session.set({ [`capture:${originalId}`]: capture });
}

function requireReview() { $("reviewed").checked = false; }

function updateState() {
  const targetIndex = capture.messages.findIndex((message) => message.sourceId === selectedTarget);
  const included = capture.messages.filter((message, index) => message.included !== false && index <= targetIndex).length;
  $("capture-summary").textContent = `${capture.messages.length} mensagens capturadas · ${included} no trecho selecionado${capture.skipped ? ` · ${capture.skipped} itens sem texto ignorados` : ""}.`;
  for (const [index, message] of capture.messages.entries()) {
    const row = document.querySelector(`[data-message-index="${index}"]`);
    row.classList.toggle("target", message.sourceId === selectedTarget);
    row.classList.toggle("excluded", message.included === false);
    row.classList.toggle("after-target", index > targetIndex);
    row.querySelector("input[type=radio]").disabled = message.role !== "customer" || message.included === false;
    row.querySelector("input[type=radio]").checked = message.sourceId === selectedTarget;
  }
  $("submit").disabled = Boolean(imported);
}

function renderMessages() {
  $("messages").replaceChildren();
  for (const [index, message] of capture.messages.entries()) {
    const card = document.createElement("article");
    card.className = "message";
    card.dataset.messageIndex = index;
    const head = document.createElement("div");
    head.className = "message-head";
    const include = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = message.included !== false;
    checkbox.addEventListener("change", () => {
      requireReview();
      message.included = checkbox.checked;
      if (!checkbox.checked && message.sourceId === selectedTarget) selectedTarget = null;
      capture.targetSourceId = selectedTarget;
      updateState(); void saveDraft();
    });
    include.append(checkbox, document.createTextNode(`Incluir mensagem ${index + 1}`));
    const roleLabel = document.createElement("label");
    roleLabel.append(document.createTextNode("Enviado por"));
    const role = document.createElement("select");
    role.setAttribute("aria-label", `Papel da mensagem ${index + 1}`);
    for (const [value, title] of [["unknown", "Conferir participante"], ["customer", "Cliente"], ["attendant", "Atendente"]]) {
      const option = document.createElement("option"); option.value = value; option.textContent = title; role.append(option);
    }
    role.value = message.role;
    role.addEventListener("change", () => {
      requireReview();
      message.role = role.value;
      if (message.role !== "customer" && message.sourceId === selectedTarget) selectedTarget = null;
      capture.targetSourceId = selectedTarget;
      updateState(); void saveDraft();
    });
    roleLabel.append(role);
    const time = document.createElement("span"); time.className = "message-time";
    time.textContent = message.displayTimestamp || "Horário não disponível";
    head.append(include, roleLabel, time);
    const text = document.createElement("textarea");
    text.setAttribute("aria-label", `Texto da mensagem ${index + 1}`);
    text.value = message.text;
    text.rows = Math.min(8, Math.max(2, message.text.split("\n").length));
    text.addEventListener("input", () => { requireReview(); message.text = text.value; void saveDraft(); });
    const targetLabel = document.createElement("label"); targetLabel.className = "target-option";
    const radio = document.createElement("input"); radio.type = "radio"; radio.name = "target";
    radio.value = message.sourceId;
    radio.addEventListener("change", () => {
      requireReview();
      selectedTarget = message.sourceId; capture.targetSourceId = selectedTarget;
      updateState(); void saveDraft();
    });
    targetLabel.append(radio, document.createTextNode("Responder a esta solicitação (cortar o histórico aqui)"));
    card.append(head, text, targetLabel); $("messages").append(card);
  }
  updateState();
}

function busy(value) {
  $("submit").disabled = value || Boolean(imported);
  $("submit").textContent = value ? "Importando trecho…" : "Processar e abrir no MAB";
  for (const input of document.querySelectorAll("#messages input, #messages select, #messages textarea, #architecture, #runtime, #new-run")) input.disabled = value || Boolean(imported);
  $("new-run").disabled = value;
  if (!value && !imported && capture) updateState();
}

async function openImported() {
  if (!imported) return;
  await chrome.tabs.create({ url: conversationUrl($("web-base").value, imported.conversationId) });
}

async function submit() {
  try {
    if (!$("reviewed").checked) throw new Error("Revise o trecho e marque a confirmação de envio antes de continuar.");
    const apiBase = localBaseUrl($("api-base").value, "API local");
    localBaseUrl($("web-base").value, "Interface MAB");
    const apiKey = $("api-key").value.trim();
    if (apiKey.startsWith("bedrock-api-key-")) throw new Error("Essa é uma chave Bedrock. Remova-a deste campo: a extensão usa somente a chave local da API do MAB; Bedrock é configurado no servidor.");
    const choices = { targetSourceId: selectedTarget, architectureMode: $("architecture").value, runtimeMode: $("runtime").value };
    const payload = buildImportPayload(capture, choices);
    const signature = JSON.stringify(payload);
    if (submittedPayload && signature !== submittedPayload) throw new Error("O trecho mudou após uma tentativa de envio. Use ‘Nova execução’ antes de reenviar; a tentativa anterior pode ter sido recebida.");
    submittedPayload = signature;
    capture.submittedPayload = signature;
    $("new-run").hidden = false;
    await chrome.storage.session.set({ settings: { apiBase, webBase: $("web-base").value.trim(), apiKey } });
    await saveDraft();
    busy(true);
    announce("Enviando o trecho revisado ao MAB local… A geração será acompanhada na conversa.");
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 25000);
    let response;
    try {
      response = await fetch(`${apiBase}/integrations/whatsapp/import`, {
        method: "POST", headers: { "Content-Type": "application/json", ...(apiKey ? { "X-API-Key": apiKey } : {}) },
        body: signature, signal: controller.signal,
      });
    } finally { clearTimeout(timeout); }
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(apiError(response.status, body.detail));
    conversationUrl($("web-base").value, body.conversationId);
    imported = body;
    capture.imported = imported;
    await saveDraft();
    announce(`${body.reused ? "Importação existente recuperada" : "Trecho importado"}: ${body.importedMessageCount} mensagens, ${body.runIds?.length || 1} execução(ões). Acompanhe a sugestão na aba do MAB.`);
    $("retry").hidden = false;
    await openImported();
  } catch (error) {
    const message = error.name === "AbortError" ? "A API demorou a responder. Tente novamente sem alterar o trecho: a mesma identificação evita duplicar a importação." : error.message === "Failed to fetch" ? "Não foi possível alcançar a API local. Confira se ela está iniciada e se o endereço e a porta estão corretos." : error.message;
    announce(message, true);
  } finally { busy(false); }
}

$("submit").addEventListener("click", submit);
$("only-target").addEventListener("click", () => {
  if (!selectedTarget) return announce("Selecione primeiro uma solicitação do cliente na lista.", true);
  for (const message of capture.messages) message.included = message.sourceId === selectedTarget;
  requireReview(); renderMessages(); void saveDraft();
  announce("Somente a solicitação selecionada será enviada. O texto continua editável; confira o conteúdo antes de confirmar.");
});
$("include-all").addEventListener("click", () => {
  for (const message of capture.messages) message.included = true;
  requireReview(); renderMessages(); void saveDraft();
  announce("Contexto reincluído. As mensagens posteriores à solicitação selecionada continuam fora do envio.");
});
$("retry").addEventListener("click", () => void openImported().catch((error) => announce(error.message, true)));
$("new-run").addEventListener("click", () => {
  capture.captureId = crypto.randomUUID(); imported = null; submittedPayload = null;
  delete capture.imported; delete capture.submittedPayload;
  $("reviewed").checked = false; $("retry").hidden = true; $("new-run").hidden = true;
  busy(false); renderMessages(); void saveDraft();
  announce("Nova identificação criada. Revise o trecho e confirme o envio para gerar outra execução.");
});
$("discard").addEventListener("click", async () => {
  await chrome.storage.session.remove(`capture:${originalId}`);
  $("capture-panel").hidden = true;
  announce("Captura descartada desta sessão. Para capturar outro trecho, volte ao WhatsApp e clique na extensão.");
});
$("runtime").addEventListener("change", () => {
  requireReview();
  $("mode-note").textContent = $("runtime").value === "real"
    ? "No modo real, o trecho revisado será enviado pelo runtime ao modelo configurado no Bedrock. Ele produz uma sugestão usando fontes controladas do protótipo."
    : "Modo simulado: valida a integração e a interface com respostas artificiais, sem invocar o modelo. Não é uma medição experimental.";
});

try {
  const values = await chrome.storage.session.get([`capture:${originalId}`, "settings"]);
  capture = values[`capture:${originalId}`];
  Object.assign(settings, values.settings || {});
  $("api-base").value = settings.apiBase; $("web-base").value = settings.webBase; $("api-key").value = settings.apiKey;
  if (!capture || capture.error) throw new Error(capture?.error || "A captura expirou. Volte ao WhatsApp Web e clique na extensão novamente.");
  selectedTarget = capture.targetSourceId || [...capture.messages].reverse().find((message) => message.role === "customer")?.sourceId;
  imported = capture.imported; submittedPayload = capture.submittedPayload;
  if (submittedPayload) {
    const submitted = JSON.parse(submittedPayload);
    $("architecture").value = submitted.architectureMode;
    $("runtime").value = submitted.runtimeMode;
    selectedTarget = submitted.targetSourceId;
    $("runtime").dispatchEvent(new Event("change"));
  }
  $("chat-title").textContent = capture.chatTitle;
  $("capture-panel").hidden = false;
  renderMessages();
  if (submittedPayload) $("new-run").hidden = false;
  if (imported) { $("retry").hidden = false; busy(false); announce("Esta captura já foi importada. Abra a conversa existente ou crie uma nova execução."); }
} catch (error) { announce(error.message, true); }

$("architecture").addEventListener("change", requireReview);
