import { LocalMabClient } from "./background-client.js";

const client = new LocalMabClient({ getSettings: async () => (await chrome.storage.session.get("settings")).settings || {} });

chrome.action.onClicked.addListener(async (tab) => {
  try {
    if (!tab.id || !tab.url || new URL(tab.url).origin !== "https://web.whatsapp.com") throw new Error("Abra uma conversa no WhatsApp Web para usar o MAB.");
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["extractor.js", "panel-core.js", "composer.js", "message-actions.js"] });
    const results = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: () => globalThis.MabWhatsAppMessages.toggle() });
    const enabled = results[0]?.result?.enabled;
    await chrome.action.setBadgeText({ tabId: tab.id, text: enabled ? "ON" : "" });
    await chrome.action.setTitle({ tabId: tab.id, title: enabled ? "MAB ativo nas mensagens recebidas · clique para desativar" : "Ativar sugestões MAB nas mensagens recebidas" });
  } catch (error) {
    await chrome.action.setBadgeText({ tabId: tab.id, text: "!" });
    await chrome.action.setTitle({ tabId: tab.id, title: error.message || "Abra uma conversa no WhatsApp Web." });
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (sender.id !== chrome.runtime.id || !sender.url || new URL(sender.url).origin !== "https://web.whatsapp.com" || !message?.type?.startsWith("mab:")) return;
  (async () => {
    switch (message.type) {
      case "mab:settings": return client.publicSettings();
      case "mab:import": return client.importCapture(message.capture, message.choices);
      case "mab:progress": return client.progress(message.conversationId, message.runIds);
      case "mab:open-details": {
        await chrome.tabs.create({ url: await client.detailUrl(message.conversationId) }); return { opened: true };
      }
      case "mab:open-settings": {
        await chrome.tabs.create({ url: chrome.runtime.getURL("options.html") }); return { opened: true };
      }
      case "mab:open-review": {
        const capture = message.capture;
        if (!capture || !/^[a-f\d-]{36}$/i.test(capture.captureId)) throw new Error("Capture novamente a conversa.");
        await chrome.storage.session.set({ [`capture:${capture.captureId}`]: capture });
        await chrome.tabs.create({ url: chrome.runtime.getURL(`review.html?capture=${capture.captureId}`) }); return { opened: true };
      }
      default: throw new Error("Ação MAB desconhecida.");
    }
  })().then((value) => sendResponse({ ok: true, value }), (error) => sendResponse({ ok: false, error: error.message || "Não foi possível acessar o MAB." }));
  return true;
});
