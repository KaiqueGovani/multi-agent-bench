export const ARCHITECTURES = new Set([
  "centralized_orchestration", "structured_workflow", "decentralized_swarm", "all_architectures",
]);

export function localBaseUrl(value, label = "Endereço") {
  let url;
  try { url = new URL(value); } catch { throw new Error(`${label}: informe uma URL local válida.`); }
  if (url.protocol !== "http:" || !["127.0.0.1", "localhost", "[::1]"].includes(url.hostname) || url.username || url.password || url.search || url.hash || url.pathname !== "/") {
    throw new Error(`${label}: use http://127.0.0.1:porta ou http://localhost:porta, sem caminho ou credenciais.`);
  }
  if (url.hostname === "[::1]") throw new Error(`${label}: use 127.0.0.1 ou localhost, autorizados pela extensão.`);
  return url.origin;
}

export function buildImportPayload(capture, choices) {
  if (!capture || !Array.isArray(capture.messages)) throw new Error("Capture uma conversa antes de continuar.");
  if (!ARCHITECTURES.has(choices.architectureMode)) throw new Error("Selecione uma arquitetura válida.");
  if (!["real", "mock"].includes(choices.runtimeMode)) throw new Error("Selecione o modo de execução.");
  const selected = capture.messages.filter((message) => message.included !== false);
  const cutoff = selected.findIndex((message) => message.sourceId === choices.targetSourceId);
  if (cutoff < 0) throw new Error("Selecione a mensagem do cliente que deve receber uma resposta.");
  const messages = selected.slice(0, cutoff + 1).map((message) => {
    const text = String(message.text ?? "").trim();
    if (!text || text.length > 8000) throw new Error("Cada mensagem precisa ter entre 1 e 8.000 caracteres. Edite ou exclua as mensagens inválidas.");
    if (!["customer", "attendant"].includes(message.role)) throw new Error("Confira quem enviou cada mensagem.");
    return {
      sourceId: String(message.sourceId ?? ""), role: message.role, text,
      ...(message.timestamp ? { timestamp: message.timestamp } : {}),
    };
  });
  if (messages.at(-1)?.role !== "customer") throw new Error("A solicitação final deve ser uma mensagem do cliente. Você pode corrigir o papel na lista.");
  if (messages.length > 200) throw new Error("Selecione no máximo 200 mensagens.");
  if (new Set(messages.map((m) => m.sourceId)).size !== messages.length || messages.some((m) => !m.sourceId || m.sourceId.length > 300)) {
    throw new Error("Os identificadores das mensagens são inválidos. Faça uma nova captura.");
  }
  if (messages.reduce((sum, message) => sum + message.text.length, 0) > 64000) throw new Error("O trecho excede 64.000 caracteres. Exclua as mensagens que não forem necessárias.");
  return {
    source: "whatsapp_web", captureId: capture.captureId,
    targetSourceId: choices.targetSourceId, chatTitle: String(capture.chatTitle ?? "Conversa WhatsApp").slice(0, 200),
    messages, architectureMode: choices.architectureMode, runtimeMode: choices.runtimeMode,
  };
}

export function conversationUrl(webBase, conversationId) {
  if (!/^[a-f\d]{8}-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{12}$/i.test(conversationId ?? "")) throw new Error("O MAB devolveu um identificador de conversa inválido.");
  const url = new URL(localBaseUrl(webBase, "Interface MAB"));
  url.searchParams.set("conversationId", conversationId);
  return url.toString();
}

export function apiError(status, detail) {
  const message = typeof detail === "string" ? detail : "Confira os dados e tente novamente.";
  if (status === 401 || status === 403) return "A API local recusou o acesso. Confira a chave da API do MAB (não é a chave Bedrock).";
  if (status === 409) return "Esta captura já foi importada com outros dados. Use ‘Nova execução’ para gerar uma nova identificação.";
  if (status === 422) return `O trecho não foi aceito: ${message}`;
  if (status === 503) return "O runtime real não está disponível. Inicie os serviços do MAB ou escolha explicitamente o modo simulado.";
  return `MAB retornou HTTP ${status}. ${message}`;
}
