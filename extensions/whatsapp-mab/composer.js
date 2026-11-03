// Public DOM editing only. This module never sends a WhatsApp message.
(() => {
  const failure = (message) => Object.assign(new Error(message), { name: "MabComposerError" });
  function insertReply({ main, isCurrent, text } = {}) {
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
    const read = (editor) => String(editor.innerText ?? editor.textContent ?? "").replace(/\r\n?/g, "\n");
    assertCurrent();
    const editor = findEditor();
    if (typeof document.execCommand !== "function") throw failure("Este navegador não oferece a inserção nativa. Use Copiar resposta e cole no WhatsApp.");
    try { editor.focus({ preventScroll: true }); }
    catch { throw failure("Não foi possível focar o campo do WhatsApp. Use Copiar resposta e cole na conversa."); }
    // focus/input handlers may synchronously switch chats or replace the editor.
    assertCurrent();
    if (findEditor() !== editor || document.activeElement !== editor) throw failure("O campo da conversa mudou ou perdeu o foco. Confira a conversa antes de tentar novamente.");
    const before = read(editor), rawText = String(editor.textContent ?? "");
    const nonText = editor.querySelector("img, svg, video, audio, canvas, [contenteditable='false'], [data-lexical-decorator='true']");
    if (nonText && !rawText.length) throw failure("O rascunho contém conteúdo não textual que não posso conferir com segurança. Ele foi preservado; use Copiar resposta para acrescentar a sugestão manualmente.");
    // Text nodes containing spaces are a real draft, unlike an empty <p><br>.
    const appended = Boolean(before.trim() || rawText.length || nonText);
    const reply = text.replace(/\r\n?/g, "\n"), addition = `${appended ? "\n\n" : ""}${reply}`;
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
      // insertText with multiline content can generate <p> elements whose
      // margins introduce extra visible lines. Native insertLineBreak creates
      // line breaks without simulating Enter or invoking the send action.
      const lines = addition.split("\n");
      for (let index = 0; index < lines.length; index++) {
        if (lines[index]) {
          assertEditor();
          if (document.execCommand("insertText", false, lines[index]) !== true) throw failure("A inserção não foi concluída. Confira o rascunho antes de repetir; você também pode copiar a resposta.");
          assertEditor();
        }
        if (index < lines.length - 1) {
          assertEditor();
          if (document.execCommand("insertLineBreak", false, null) !== true) throw failure("A inserção não foi concluída. Confira o rascunho antes de repetir; você também pode copiar a resposta.");
          assertEditor();
        }
      }
      if (read(editor) !== `${appended ? before : ""}${addition}`) throw failure("Não foi possível confirmar a inserção completa. Confira o rascunho no WhatsApp antes de tentar novamente; você também pode copiar a resposta.");
      return { appended };
    } catch (error) {
      if (error?.name === "MabComposerError") throw error;
      throw failure("A inserção nativa não foi concluída. Confira o rascunho no WhatsApp e use Copiar resposta se necessário.");
    }
  }
  globalThis.MabWhatsAppComposer = { insertReply };
})();
