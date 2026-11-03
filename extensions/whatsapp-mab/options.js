import { localBaseUrl } from "./import-core.js";
const $ = (id) => document.getElementById(id);
const settings = (await chrome.storage.session.get("settings")).settings || {};
$("api-base").value = settings.apiBase || "http://127.0.0.1:8000";
$("web-base").value = settings.webBase || "http://127.0.0.1:3100";
$("api-key").value = settings.apiKey || "";
$("save").addEventListener("click", async () => {
  try {
    const apiBase = localBaseUrl($("api-base").value, "API local"), webBase = localBaseUrl($("web-base").value, "Interface MAB"), apiKey = $("api-key").value.trim();
    if (apiKey.startsWith("bedrock-api-key-")) throw new Error("A chave Bedrock fica somente no servidor. Informe a chave local da API do MAB.");
    await chrome.storage.session.set({ settings: { apiBase, webBase, apiKey } });
    $("error").hidden = true; $("status").hidden = false; $("status").textContent = "Conexão salva. Volte ao WhatsApp e gere uma sugestão pelo painel MAB.";
  } catch (error) { $("status").hidden = true; $("error").hidden = false; $("error").textContent = error.message; }
});
