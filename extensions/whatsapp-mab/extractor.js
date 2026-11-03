// Executed in Chrome's isolated world only after an explicit click on the action.
// No WhatsApp internals, network, cookies, hidden stores or automatic scrolling.
(() => {
  function captureWhatsApp(root = document) {
    const main = root.querySelector("#main");
    if (!main) throw new Error("Abra uma conversa no WhatsApp Web antes de capturar.");
    const chatTitle = main.querySelector("header [data-testid='conversation-info-header-chat-title']")?.textContent
      || main.querySelector("header span[title]")?.getAttribute("title")
      || main.querySelector("header [title]")?.getAttribute("title")
      || (main.querySelector("header")?.innerText || main.querySelector("header")?.textContent || "Conversa WhatsApp").split("\n")[0];
    const seen = new Set();
    const messages = [];
    let skipped = 0;
    // The main conversation scope excludes the contact list and search previews.
    const rows = [...main.querySelectorAll("[data-id]")];
    const bubbles = rows.length ? rows : [...main.querySelectorAll(".message-in, .message-out")];
    for (const bubble of bubbles) {
      if (bubble.closest("[data-mab-ui]")) continue;
      if (bubble.closest("[aria-hidden='true']")) continue;
      const owner = bubble.closest("[data-id]") || bubble.querySelector("[data-id]");
      const sourceId = owner?.getAttribute("data-id");
      if (!sourceId || seen.has(sourceId)) continue;
      const content = bubble.querySelector(".copyable-text[data-pre-plain-text]") || bubble.querySelector("[data-pre-plain-text]") || bubble;
      // A quoted prior message must not become the current message a second time.
      const textNodes = [...content.querySelectorAll("[data-testid='selectable-text'], .selectable-text")]
        .filter((node, index, nodes) => !nodes.some((other, otherIndex) => otherIndex < index && other.contains(node)))
        .filter((node) => !node.closest("[data-mab-ui]"))
        .filter((node) => !node.closest("[data-testid='quoted-message'], [data-testid='quoted-message-container'], [data-testid='quoted-text'], [data-testid='msg-quoted'], .quoted-mention"));
      let text = textNodes.map((node) => node.innerText ?? node.textContent ?? "").map((value) => value.trim()).filter(Boolean).join("\n");
      if (!text) {
        const hasMedia = !!bubble.querySelector("img[src^='blob:'], video, audio, [data-testid='audio-play'], [data-testid='document-thumb'], [data-icon='document'], [data-icon='audio-play']");
        if (hasMedia) text = "[Anexo presente no WhatsApp. Conteúdo não capturado; descreva em texto antes de solicitar análise.]";
      }
      if (!text) { skipped++; continue; }
      seen.add(sourceId);
      const prePlainText = content.getAttribute("data-pre-plain-text") || "";
      const senderLabels = [...bubble.querySelectorAll("[aria-label]")]
        .filter((node) => !node.closest("[data-testid='quoted-message'], [data-testid='quoted-message-container'], [data-testid='msg-quoted']"))
        .map((node) => node.getAttribute("aria-label")?.trim() || "");
      const sender = prePlainText.replace(/^\[[^\]]+\]\s*/, "").replace(/:\s*$/, "").trim();
      let role = "unknown";
      if (bubble.classList.contains("message-out") || bubble.querySelector(".message-out") || senderLabels.some((label) => /^(Você|Voce|You):?$/i.test(label)) || /^true_/.test(sourceId)) role = "attendant";
      else if (bubble.classList.contains("message-in") || bubble.querySelector(".message-in") || senderLabels.some((label) => label.replace(/:\s*$/, "").trim() === chatTitle.trim()) || sender === chatTitle.trim() || /^false_/.test(sourceId)) role = "customer";
      messages.push({ sourceId, role, text, displayTimestamp: prePlainText.match(/^\[([^\]]+)\]/)?.[1] || "", included: true });
    }
    if (!messages.length) throw new Error("Não encontrei mensagens no trecho carregado. Abra a conversa, aguarde as mensagens e tente novamente.");
    if (messages.length > 200) throw new Error("O trecho carregado tem mais de 200 mensagens. Abra um trecho menor antes de capturar.");
    return { chatTitle: chatTitle.trim(), messages, skipped, capturedAt: new Date().toISOString(), historyScope: "rendered_only" };
  }
  globalThis.MabWhatsAppCapture = { captureWhatsApp };
})();
