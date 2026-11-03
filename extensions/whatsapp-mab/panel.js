(() => {
  if (globalThis.MabWhatsAppPanel) return;
  const core = globalThis.MabPanelCore;
  let host, shadow, capture, targetId, chatMain, chatTitle, chatIdentity, imported, submitted, activeRun, pollTimer, epoch = 0, choosing = false, busy = false, invalid = false, lastProgress;
  const $ = (id) => shadow.getElementById(id);
  const rpc = async (type, data = {}) => {
    const response = await chrome.runtime.sendMessage({ type, ...data });
    if (!response?.ok) throw new Error(response?.error || "A extensão foi recarregada. Clique novamente no ícone MAB.");
    return response.value;
  };
  function status(text, error = false) {
    $("status").textContent = text; $("status").className = error ? "status error" : "status";
  }
  function stopWatching() { epoch++; clearTimeout(pollTimer); }
  function titleNow() {
    const main = document.querySelector("#main"), header = main?.querySelector("header");
    const title = header?.querySelector("[data-testid='conversation-info-header-chat-title']")?.textContent || header?.querySelector("span[title]")?.getAttribute("title") || header?.querySelector("[title]")?.getAttribute("title") || header?.innerText || header?.textContent || "";
    return { main, title: title.split("\n")[0], identity: main?.querySelector("footer [contenteditable='true'][aria-label]")?.getAttribute("aria-label") || "" };
  }
  function isCurrent() {
    const current = titleNow();
    if (invalid || current.main !== chatMain || current.title.trim() !== chatTitle || current.identity !== chatIdentity) return false;
    // Different contacts may share a display name. If every captured message
    // disappeared from the rendered chat, stop rather than attach an old result.
    const visibleIds = new Set([...current.main.querySelectorAll("[data-id]")].map((node) => node.getAttribute("data-id")));
    return Boolean(capture?.messages.some((message) => visibleIds.has(message.sourceId)));
  }
  function invalidate() {
    if (invalid || !shadow) return;
    invalid = true; stopWatching(); choosing = false; setBusy(false);
    $("target").value = ""; $("chat").textContent = "A conversa mudou"; $("results").hidden = true; $("copy").disabled = true;
    $("generate").disabled = true; $("choose").disabled = true;
    status("Atualize o trecho para usar o MAB nesta conversa.");
  }
  function setBusy(value) {
    busy = value;
    for (const id of ["generate", "choose", "target", "context", "architecture", "runtime", "new"]) $(id).disabled = value || invalid;
    $("generate").textContent = value ? "Gerando sugestão…" : submitted && !imported ? "Tentar novamente" : "Gerar sugestão";
    $("refresh").disabled = value;
  }
  function payloadCapture() {
    if (!capture || !isCurrent()) throw new Error("A conversa mudou. Atualize o trecho antes de continuar.");
    return core.selectContext(capture, targetId, $("context").value, $("target").value);
  }
  function renderContext() {
    try {
      const selected = payloadCapture();
      $("count").textContent = `${selected.messages.length} mensagem${selected.messages.length === 1 ? "" : "s"} até a solicitação · somente o trecho carregado`;
      $("context-preview").replaceChildren();
      for (const message of selected.messages) {
        const line = document.createElement("p");
        line.textContent = `${message.role === "customer" ? "Cliente" : message.role === "attendant" ? "Atendente" : "Participante não identificado"}: ${message.text}`;
        $("context-preview").append(line);
      }
    } catch { $("count").textContent = "Escolha uma solicitação do cliente."; }
  }
  function refresh() {
    stopWatching(); imported = null; submitted = null; lastProgress = null; activeRun = null; choosing = false;
    $("results").hidden = true; $("copy").disabled = true;
    try {
      capture = { ...globalThis.MabWhatsAppCapture.captureWhatsApp(), captureId: crypto.randomUUID() };
      const current = titleNow(); chatMain = current.main; chatTitle = current.title.trim(); chatIdentity = current.identity; invalid = false;
      const target = core.latestCustomer(capture);
      if (!target) throw new Error("Não encontrei uma mensagem recebida do cliente. Use a revisão completa para conferir os participantes.");
      targetId = target.sourceId; $("target").value = target.text; $("chat").textContent = capture.chatTitle;
      $("results").hidden = true; $("new").hidden = true;
      setBusy(false); renderContext(); status("Pronto. Confira a solicitação e gere uma sugestão.");
    } catch (error) { invalid = true; setBusy(false); status(error.message, true); }
  }
  function chooseMessage(event) {
    if (!choosing || !chatMain?.contains(event.target)) return;
    const row = event.target.closest("[data-id]");
    if (!row) return;
    event.preventDefault(); event.stopImmediatePropagation();
    const latest = globalThis.MabWhatsAppCapture.captureWhatsApp();
    const message = latest.messages.find((item) => item.sourceId === row.getAttribute("data-id"));
    if (!message || message.role !== "customer") { status("Escolha uma mensagem recebida do cliente, não uma resposta enviada.", true); return; }
    if (submitted) { status("Use ‘Nova sugestão’ antes de escolher outra solicitação.", true); choosing = false; return; }
    capture = { ...latest, captureId: capture.captureId }; targetId = message.sourceId; $("target").value = message.text;
    choosing = false; $("choose").textContent = "Escolher outra mensagem";
    const previousOutline = row.style.outline; row.style.outline = "2px solid #25a77d";
    setTimeout(() => { row.style.outline = previousOutline; }, 1500);
    renderContext(); status("Solicitação selecionada. Mensagens posteriores ficam fora do contexto.");
  }
  function renderRuns(progress) {
    lastProgress = progress;
    const previous = activeRun;
    activeRun = progress.runs.some((run) => run.id === activeRun) ? activeRun : progress.runs[0]?.id;
    $("results").hidden = false; $("tabs").replaceChildren();
    for (const run of progress.runs) {
      const button = document.createElement("button"); button.type = "button"; button.className = run.id === activeRun ? "tab selected" : "tab";
      button.setAttribute("role", "tab"); button.setAttribute("aria-selected", String(run.id === activeRun)); button.textContent = run.name;
      button.addEventListener("click", () => { activeRun = run.id; renderRuns(lastProgress); }); $("tabs").append(button);
    }
    const run = progress.runs.find((item) => item.id === activeRun);
    $("response").textContent = run?.text || run?.error || (run?.finished ? "Esta execução terminou sem texto de resposta disponível." : "Aguardando a resposta desta arquitetura…");
    const state = run?.error ? "Falha na execução" : run?.reviewRequired ? "Revisão profissional indicada" : run?.finished ? "Sugestão pronta" : "Processando";
    $("metrics").textContent = [state, run?.durationMs != null ? `${(run.durationMs / 1000).toFixed(1)} s` : "", run?.tokens != null ? `${run.tokens.toLocaleString("pt-BR")} tokens` : ""].filter(Boolean).join(" · ");
    $("copy").disabled = !run?.text;
    if (previous !== activeRun) $("response").scrollTop = 0;
  }
  async function poll(token, started = Date.now()) {
    if (token !== epoch || !isCurrent() || $("panel").hidden) return;
    try {
      const progress = await rpc("mab:progress", { conversationId: imported.conversationId, runIds: imported.runIds });
      if (token !== epoch || !isCurrent() || $("panel").hidden) return;
      renderRuns(progress);
      if (progress.finished) { setBusy(false); status(progress.runs.some((run) => run.error) ? "Processamento encerrado. Confira as respostas e eventuais falhas." : "Sugestão pronta. Revise o texto antes de usar no atendimento."); return; }
      if (Date.now() - started > 180000) { setBusy(false); status("O processamento continua no MAB. Use ‘Tentar novamente’ para retomar o acompanhamento.", true); return; }
      status(`Aguardando o MAB… ${progress.ready}/${progress.runs.length} resposta(s) disponível(is).`);
      pollTimer = setTimeout(() => void poll(token, started), 1800);
    } catch (error) { if (token === epoch && isCurrent()) { setBusy(false); status(`${error.message} Tente novamente para retomar o acompanhamento.`, true); } }
  }
  async function generate() {
    if (busy) return;
    const token = ++epoch;
    try {
      const selected = payloadCapture();
      const choices = { targetSourceId: targetId, architectureMode: $("architecture").value, runtimeMode: $("runtime").value };
      const signature = JSON.stringify({ selected, choices });
      if (submitted && submitted !== signature) throw new Error("O trecho ou a arquitetura mudou. Use ‘Nova sugestão’ antes de processar novamente.");
      submitted = signature; $("new").hidden = false; setBusy(true);
      status(imported ? "Retomando o acompanhamento…" : "Enviando o trecho revisado ao MAB local…");
      if (!imported) {
        const response = await rpc("mab:import", { capture: selected, choices });
        if (token !== epoch || !isCurrent() || $("panel").hidden) return;
        imported = response;
      }
      await poll(token);
    } catch (error) { if (token === epoch && isCurrent()) { setBusy(false); status(error.message, true); } }
  }
  function create() {
    host = document.createElement("div"); host.id = "mab-whatsapp-assistant";
    host.style.cssText = "position:fixed;right:18px;top:76px;z-index:2147483000;max-width:calc(100vw - 32px);";
    shadow = host.attachShadow({ mode: "open" });
    shadow.innerHTML = `<style>
      :host{all:initial;color-scheme:light}*{box-sizing:border-box}[hidden]{display:none!important}button,select,textarea{font:inherit}button{cursor:pointer}button:disabled{opacity:.55;cursor:default}button:focus-visible,select:focus-visible,textarea:focus-visible,summary:focus-visible{outline:3px solid #75b89f;outline-offset:2px}.pill{border:0;border-radius:25px;background:#225e4b;color:white;padding:11px 18px;font:650 13px system-ui;box-shadow:0 3px 14px #0003;float:right}.panel{width:380px;max-width:calc(100vw - 32px);max-height:80vh;overflow:auto;border:1px solid #d6e3dc;border-radius:15px;box-shadow:0 12px 46px #142e2438;background:#f9fcfa;font:13px/1.45 system-ui,-apple-system,sans-serif;color:#20483b}.head{position:sticky;top:0;background:#edf5ef;z-index:2;display:flex;align-items:center;padding:13px 16px;border-bottom:1px solid #dbe7df;gap:10px}.logo{font-weight:800;font-size:19px}.subtitle{font-size:11px;color:#587268}.grow{flex:1}.icon{border:0;background:transparent;color:#365f4e;font-size:20px;padding:0 5px}.body{padding:15px 16px}.chat{font-size:15px;font-weight:700;margin:0 0 11px;overflow-wrap:anywhere}.label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#5b7769}.target{display:block;width:100%;resize:vertical;min-height:72px;max-height:145px;border:1px solid #d3e1d8;border-radius:8px;padding:10px;background:#fff;color:#224334;margin:6px 0;font:13px/1.45 system-ui}.link{border:0;background:transparent;padding:3px 0;color:#287457;font-size:12px;text-decoration:underline;text-underline-offset:3px}.row{display:flex;gap:10px;margin-top:12px}.field{flex:1;min-width:0}.field label{font-size:11px;font-weight:650}.field select{display:block;width:100%;border:1px solid #cfdfd4;border-radius:7px;background:white;color:#254c3c;padding:8px 6px;margin-top:4px;font-size:12px}.count{font-size:11px;color:#637b6d;margin:8px 0}.primary{width:100%;border:0;border-radius:8px;padding:11px;background:#24674f;color:#fff;font-weight:700;font-size:13px;margin-top:11px}.secondary{border:1px solid #cadcd0;border-radius:7px;background:#fff;color:#2e654d;padding:7px 11px;font-size:12px}.status{font-size:12px;color:#3c7059;margin:10px 0;white-space:pre-wrap}.error{color:#9d4229}.results{margin-top:14px;border-top:1px solid #dae6dd;padding-top:13px}.tabs{display:flex;gap:5px}.tab{flex:1;border:1px solid #d3e2d8;border-radius:7px;background:#f5f9f6;color:#466452;padding:7px 3px;font-size:11px}.selected{background:#dfeee4;border-color:#83b296;color:#24563d;font-weight:750}.metrics{font-size:10px;color:#63806c;margin:9px 0}.response{white-space:pre-wrap;overflow-wrap:anywhere;max-height:260px;overflow:auto;background:white;border:1px solid #dce7df;border-radius:9px;padding:11px;font:13px/1.5 system-ui;color:#244b38}.response-actions{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:8px}.hint{font-size:10px;color:#708575;margin:9px 0 0}details{margin-top:11px;font-size:11px;color:#5c7868}summary{cursor:pointer}.context-preview{max-height:200px;overflow:auto;font-size:11px}.context-preview p{white-space:pre-wrap;border-left:2px solid #d6e5da;padding:5px 0 5px 9px}.footer{padding:10px 16px;border-top:1px solid #e0eae3;background:#f1f7f3;display:flex;justify-content:space-between}.small{font-size:10px;color:#728576}
    </style><button id="pill" class="pill" type="button" hidden>MAB · Assistente</button><section id="panel" class="panel" aria-label="Assistente MAB"><header class="head"><span class="logo">MAB</span><div class="grow"><strong>Assistente de atendimento</strong><div class="subtitle">Sugestões sem sair da conversa</div></div><button id="collapse" type="button" class="icon" aria-label="Recolher assistente">−</button><button id="close" type="button" class="icon" aria-label="Fechar assistente">×</button></header><div class="body"><p id="chat" class="chat"></p><label class="label" for="target">Solicitação do cliente</label><textarea id="target" class="target" rows="3" aria-label="Solicitação do cliente"></textarea><button id="choose" type="button" class="link">Escolher outra mensagem</button><div class="row"><div class="field"><label for="context">Contexto</label><select id="context"><option value="recent">Últimas 10 mensagens</option><option value="target">Só esta solicitação</option></select></div><div class="field"><label for="architecture">Arquitetura</label><select id="architecture"><option value="centralized_orchestration">Centralizada</option><option value="structured_workflow">Workflow</option><option value="decentralized_swarm">Swarm</option><option value="all_architectures">Comparar as três</option></select></div></div><p id="count" class="count"></p><details><summary>Conferir contexto e opções</summary><div id="context-preview" class="context-preview"></div><div class="field"><label for="runtime">Execução</label><select id="runtime"><option value="real">Real · Bedrock</option><option value="mock">Simulada · sem modelo</option></select></div><p class="hint">O modo real envia o trecho revisado ao modelo. Fontes controladas do protótipo; mídias não são lidas.</p><button id="full-review" type="button" class="link">Revisar todo o trecho em uma aba</button><p id="connection" class="hint"></p><button id="settings" type="button" class="link">Configurar conexão local</button></details><button id="generate" type="button" class="primary">Gerar sugestão</button><p id="status" class="status" role="status" aria-live="polite"></p><section id="results" class="results" hidden><div id="tabs" class="tabs" role="tablist" aria-label="Respostas por arquitetura"></div><p id="metrics" class="metrics"></p><div id="response" class="response" role="tabpanel" tabindex="0"></div><div class="response-actions"><button id="copy" class="secondary" type="button" disabled>Copiar resposta</button><button id="details" class="link" type="button">Detalhes no MAB ↗</button></div><p class="hint">Revise antes de usar. Nada é enviado ao WhatsApp.</p></section><button id="new" type="button" class="link" hidden>Nova sugestão</button></div><footer class="footer"><span class="small">Captura manual · conexão local</span><button id="refresh" class="link" type="button">Atualizar trecho</button></footer></section>`;
    document.body.append(host);
    $("generate").addEventListener("click", (event) => { if (event.isTrusted) void generate(); });
    $("target").addEventListener("input", renderContext); $("context").addEventListener("change", renderContext);
    $("refresh").addEventListener("click", refresh);
    $("choose").addEventListener("click", () => { choosing = !choosing; $("choose").textContent = choosing ? "Cancelar seleção" : "Escolher outra mensagem"; status(choosing ? "Clique na mensagem recebida do cliente dentro da conversa." : "Seleção cancelada."); });
    $("new").addEventListener("click", (event) => { if (!event.isTrusted || !capture) return; stopWatching(); imported = null; submitted = null; lastProgress = null; activeRun = null; capture.captureId = crypto.randomUUID(); $("new").hidden = true; $("results").hidden = true; setBusy(false); status("Pronto para gerar outra sugestão com este trecho."); });
    $("copy").addEventListener("click", async (event) => { if (!event.isTrusted) return; if (!isCurrent()) return invalidate(); try { const run = lastProgress?.runs.find((item) => item.id === activeRun); if (run?.text) { await navigator.clipboard.writeText(run.text); status("Resposta copiada. Revise e cole no atendimento quando desejar."); } } catch { status("Não foi possível copiar. Selecione o texto da resposta para copiar manualmente.", true); } });
    $("details").addEventListener("click", (event) => event.isTrusted && imported && void rpc("mab:open-details", { conversationId: imported.conversationId }).catch((error) => status(error.message, true)));
    $("settings").addEventListener("click", (event) => event.isTrusted && void rpc("mab:open-settings").catch((error) => status(error.message, true)));
    $("full-review").addEventListener("click", (event) => { if (!event.isTrusted) return; try { void rpc("mab:open-review", { capture: payloadCapture() }).catch((error) => status(error.message, true)); } catch (error) { status(error.message, true); } });
    const collapse = () => { stopWatching(); choosing = false; $("panel").hidden = true; $("pill").hidden = false; setBusy(false); };
    $("collapse").addEventListener("click", collapse); $("close").addEventListener("click", collapse);
    $("pill").addEventListener("click", show);
    document.addEventListener("click", chooseMessage, true);
    document.addEventListener("pointerdown", (event) => { if (capture && !host.contains(event.target) && !chatMain?.contains(event.target) && event.target.closest?.("[role='row'], [data-testid='cell-frame-container']")) invalidate(); }, true);
    const observer = new MutationObserver(() => { if (capture && !invalid && !isCurrent()) invalidate(); });
    observer.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ["aria-label", "data-id"] });
    refresh();
    void rpc("mab:settings").then((settings) => { $("connection").textContent = `${settings.apiBase} · chave ${settings.hasApiKey ? "configurada" : "não configurada"}`; }).catch((error) => status(error.message, true));
  }
  function show() {
    if (!host) return create();
    $("panel").hidden = false; $("pill").hidden = true;
    if (!isCurrent()) refresh();
    else if (imported && !lastProgress?.finished) { setBusy(true); void poll(++epoch); }
  }
  globalThis.MabWhatsAppPanel = { toggle() { if (!host) create(); else if ($("panel").hidden) show(); else { stopWatching(); $("panel").hidden = true; $("pill").hidden = false; setBusy(false); } } };
})();
