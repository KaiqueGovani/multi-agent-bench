import { apiError, buildImportPayload, conversationUrl, localBaseUrl } from "./import-core.js";
import "./panel-core.js";

export class LocalMabClient {
  constructor({ getSettings, fetchImpl }) {
    this.getSettings = getSettings;
    // Native worker fetch requires its global receiver. A bare reference stored
    // on this client would be invoked with the LocalMabClient as `this`.
    this.fetchImpl = fetchImpl ?? globalThis.fetch.bind(globalThis);
  }
  async settings() {
    const raw = await this.getSettings();
    return { apiBase: localBaseUrl(raw.apiBase || "http://127.0.0.1:8000", "API local"), webBase: localBaseUrl(raw.webBase || "http://127.0.0.1:3100", "Interface MAB"), apiKey: raw.apiKey || "" };
  }
  async publicSettings() {
    const { apiBase, webBase, apiKey } = await this.settings();
    return { apiBase, webBase, hasApiKey: Boolean(apiKey) };
  }
  async json(path, options = {}) {
    const settings = await this.settings();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 25000);
    try {
      const response = await this.fetchImpl(`${settings.apiBase}${path}`, {
        ...options, headers: { "Content-Type": "application/json", ...(settings.apiKey ? { "X-API-Key": settings.apiKey } : {}) }, signal: controller.signal,
      });
      const value = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(apiError(response.status, value.detail));
      return value;
    } catch (error) {
      if (error.name === "AbortError") throw new Error("A API local demorou a responder. Tente novamente: a mesma identificação evita duplicar a importação.");
      if (error instanceof TypeError && /illegal invocation|incompatible receiver/i.test(error.message)) throw new Error("A extensão não conseguiu iniciar a requisição. Recarregue a extensão e a aba do WhatsApp e tente novamente.");
      if (error instanceof TypeError) throw new Error("Não foi possível alcançar o MAB local. Confira os serviços e a conexão nas configurações.");
      throw error;
    } finally { clearTimeout(timer); }
  }
  async importCapture(capture, choices) {
    const payload = buildImportPayload(capture, choices);
    const result = await this.json("/integrations/whatsapp/import", { method: "POST", body: JSON.stringify(payload) });
    const settings = await this.settings();
    conversationUrl(settings.webBase, result.conversationId);
    if (!Array.isArray(result.runIds) || !result.runIds.length || result.runIds.some((id) => !/^[a-f\d-]{36}$/i.test(id))) throw new Error("O MAB devolveu execuções inválidas.");
    return result;
  }
  async progress(conversationId, runIds) {
    conversationUrl("http://localhost", conversationId);
    const data = await this.json(`/conversations/${conversationId}`);
    return globalThis.MabPanelCore.summarizeRuns(data, runIds);
  }
  async detailUrl(conversationId) { return conversationUrl((await this.settings()).webBase, conversationId); }
}
