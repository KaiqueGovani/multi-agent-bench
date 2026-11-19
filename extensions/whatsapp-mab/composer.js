// Public DOM editing only. This module never sends a WhatsApp message.
(() => {
  const failure = (message) => Object.assign(new Error(message), { name: "MabComposerError" });
  const blocks = new Set(["DIV", "P", "LI", "UL", "OL", "BLOCKQUOTE", "PRE"]);
  const normalize = (text) => String(text).replace(/\r\n?/g, "\n").replace(/\u00a0/g, " ").replace(/[\u200b\ufeff]/g, "");
  function readDraft(editor, view, formatted = false, codeMarker = "`") {
    // Read public DOM only: innerText can add paragraph margins, while
    // textContent drops both <br> and paragraph boundaries.
    const readNode = (node) => {
      if (node.nodeType === 3) return node.nodeValue || "";
      if (node.nodeType !== 1) return "";
      if (node.tagName === "BR") return "\n";
      if (node.tagName === "IMG") return node.getAttribute("alt") || "";
      const children = [...node.childNodes];
      if (blocks.has(node.tagName) && children.length === 1 && children[0].nodeName === "BR") return "";
      let value = "", previousBlock = false;
      for (const child of children) {
        const block = blocks.has(child.nodeName);
        if (value && (block || previousBlock)) value += "\n";
        // Empty paragraphs still represent a blank line between blocks.
        else if (previousBlock) value += "\n";
        value += readNode(child); previousBlock = block;
      }
      if (!formatted || node === editor || !value) return value;
      const style = view.getComputedStyle(node), parentStyle = view.getComputedStyle(node.parentElement || editor);
      if (["CODE", "PRE"].includes(node.tagName) || (/monospace/i.test(style.fontFamily || "") && !/monospace/i.test(parentStyle.fontFamily || ""))) return `${codeMarker}${value}${codeMarker}`;
      if (["B", "STRONG"].includes(node.tagName) || (Number(style.fontWeight) >= 600 && Number(parentStyle.fontWeight) < 600)) value = `*${value}*`;
      if (["I", "EM"].includes(node.tagName) || (style.fontStyle === "italic" && parentStyle.fontStyle !== "italic")) value = `_${value}_`;
      if (["S", "STRIKE", "DEL"].includes(node.tagName) || ((style.textDecorationLine || "").includes("line-through") && !(parentStyle.textDecorationLine || "").includes("line-through"))) value = `~${value}~`;
      return value;
    };
    return editor.childNodes.length ? readNode(editor) : String(editor.innerText ?? editor.textContent ?? "");
  }
  const matches = (actual, expected) => normalize(actual) === normalize(expected) || normalize(actual) === `${normalize(expected)}\n`;
  async function insertReply({ main, isCurrent, text } = {}) {
    if (typeof text !== "string" || !text.trim()) throw failure("Não há uma resposta para inserir na conversa.");
    const document = main?.ownerDocument, view = document?.defaultView;
    if (!document || !view || typeof isCurrent !== "function") throw failure("Abra a conversa novamente antes de inserir a resposta.");
    const assertCurrent = () => {
      let current = false;
      try { current = Boolean(isCurrent()); } catch { /* Fail closed on stale state. */ }
      if (!current || !main.isConnected || document.querySelector("#main") !== main) throw failure("A conversa mudou. Abra a sugestão novamente antes de inserir a resposta.");
    };
    const visible = (editor) => {
      if (editor.closest("[data-mab-ui], [hidden], [inert], [aria-hidden='true']") || editor.hasAttribute("disabled") || editor.getAttribute("aria-disabled") === "true" || editor.getAttribute("aria-readonly") === "true" || editor.readOnly || editor.disabled) return false;
      if (!editor.getClientRects().length) return false;
      for (let node = editor; node && main.contains(node); node = node.parentElement) {
        const style = view.getComputedStyle(node);
        if (style.display === "none" || style.visibility === "hidden" || style.visibility === "collapse" || style.opacity === "0") return false;
      }
      return true;
    };
    const findEditor = () => {
      const candidates = [...main.querySelectorAll("footer [contenteditable='true'][role='textbox']")].filter(visible);
      if (candidates.length !== 1) throw failure("Não foi possível identificar um único campo de mensagem disponível. Abra o campo do WhatsApp e tente novamente, ou copie a resposta.");
      return candidates[0];
    };
    const read = (editor) => readDraft(editor, view);
    assertCurrent();
    const editor = findEditor();
    try { editor.focus({ preventScroll: true }); }
    catch { throw failure("Não foi possível focar o campo do WhatsApp. Use Copiar resposta e cole na conversa."); }
    // focus/input handlers may synchronously switch chats or replace the editor.
    assertCurrent();
    if (findEditor() !== editor || document.activeElement !== editor) throw failure("O campo da conversa mudou ou perdeu o foco. Confira a conversa antes de tentar novamente.");
    const codeMarkers = ["`", "```"];
    const before = read(editor), beforeFormatted = codeMarkers.map((marker) => readDraft(editor, view, true, marker)), rawText = String(editor.textContent ?? "");
    const nonText = editor.querySelector("img, svg, video, audio, canvas, [contenteditable='false'], [data-lexical-decorator='true']");
    if (nonText && !rawText.length) throw failure("O rascunho contém conteúdo não textual que não posso conferir com segurança. Ele foi preservado; use Copiar resposta para acrescentar a sugestão manualmente.");
    // Text nodes containing spaces are a real draft, unlike an empty <p><br>.
    const appended = Boolean(before.length || rawText.length || nonText);
    if (typeof globalThis.MabWhatsAppFormatter?.toWhatsApp !== "function") throw failure("Recarregue a extensão e a página do WhatsApp antes de inserir a resposta.");
    const reply = globalThis.MabWhatsAppFormatter.toWhatsApp(text), addition = `${appended ? "\n\n" : ""}${reply}`;
    const selection = document.getSelection?.() || view.getSelection?.();
    if (!selection || typeof document.createRange !== "function") throw failure("Não foi possível posicionar o cursor no WhatsApp. Use Copiar resposta.");
    try {
      const range = document.createRange(); range.selectNodeContents(editor);
      // Replacing only an empty placeholder avoids adding a leading blank line.
      // A real draft is never selected/replaced: the caret stays at its end.
      if (appended) range.collapse(false);
      selection.removeAllRanges(); selection.addRange(range);
      const assertEditor = () => {
        assertCurrent();
        if (document.activeElement !== editor || !editor.contains(selection.anchorNode) || findEditor() !== editor) throw failure("O campo do WhatsApp perdeu o foco durante a inserção. Confira o rascunho antes de tentar novamente.");
      };
      const expected = `${appended ? before : ""}${addition}`;
      const verify = () => matches(read(editor), expected) || codeMarkers.some((marker, index) => matches(readDraft(editor, view, true, marker), `${appended ? beforeFormatted[index] : ""}${addition}`));
      const settle = async () => { await Promise.resolve(); await new Promise((resolve) => view.setTimeout(resolve, 50)); assertEditor(); };
      let handled = false;
      if (typeof view.DataTransfer === "function" && typeof view.ClipboardEvent === "function") {
        // Give the editor the entire plain-text paste. Its own paste handler
        // creates the line/paragraph nodes and updates its internal state.
        // This does not touch the system clipboard or invoke the send action.
        const clipboardData = new view.DataTransfer(); clipboardData.setData("text/plain", addition);
        const event = new view.ClipboardEvent("paste", { clipboardData, bubbles: true, cancelable: true, composed: true });
        assertEditor();
        handled = !editor.dispatchEvent(event) || event.defaultPrevented;
        await settle();
        if (verify()) return { appended };
        // Never repeat a paste which the editor consumed or partly inserted.
        if (handled || read(editor) !== before) throw failure("Não foi possível confirmar a inserção completa. Confira o rascunho no WhatsApp antes de tentar novamente; você também pode copiar a resposta.");
      }
      assertEditor();
      if (typeof document.execCommand !== "function") throw failure("Este navegador não oferece a inserção nativa. Use Copiar resposta e cole no WhatsApp.");
      // A single native insertion is a fallback for editors with no paste
      // handler. Per-line insertLineBreak can be ignored by controlled editors.
      const inserted = document.execCommand("insertText", false, addition);
      await settle();
      if (!verify()) throw failure(inserted === false ? "A inserção não foi concluída. Confira o rascunho antes de repetir; você também pode copiar a resposta." : "Não foi possível confirmar a inserção completa. Confira o rascunho no WhatsApp antes de tentar novamente; você também pode copiar a resposta.");
      return { appended };
    } catch (error) {
      if (error?.name === "MabComposerError") throw error;
      throw failure("A inserção nativa não foi concluída. Confira o rascunho no WhatsApp e use Copiar resposta se necessário.");
    }
  }
  globalThis.MabWhatsAppComposer = { insertReply };
})();
