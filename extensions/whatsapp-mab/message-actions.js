(() => {
  if (globalThis.MabWhatsAppMessages) return;
  const core = globalThis.MabPanelCore;
  const bindings = new Map();
  const drafts = new Map();
  const markers = new Map();
  let enabled = false, current = null, observer = null, scanTimer = null, activeChat = null, sequence = 0;
  const rpc = async (type, data = {}) => {
    const reply = await chrome.runtime.sendMessage({ type, ...data });
    if (!reply?.ok) throw new Error(reply?.error || "A extensão foi recarregada. Clique novamente no ícone MAB.");
    return reply.value;
  };
  function chat() {
    const main = document.querySelector("#main"), header = main?.querySelector("header");
    const title = (header?.querySelector("[data-testid='conversation-info-header-chat-title']")?.textContent || header?.querySelector("span[title]")?.getAttribute("title") || header?.querySelector("[title]")?.getAttribute("title") || header?.innerText || header?.textContent || "").split("\n")[0].trim();
    // Identity is read only from the visible composer, kept in memory, never sent.
    const recipient = main?.querySelector("footer [contenteditable='true'][aria-label]")?.getAttribute("aria-label") || "";
    return { main, title, recipient };
  }
  function sameChat(a, b) { return Boolean(a && b && a.main === b.main && a.title === b.title && a.recipient === b.recipient); }
  function valid(state) {
    return enabled && current === state && sameChat(state.chat, chat()) && state.chat.main?.contains(state.row) && state.row.getAttribute("data-id") === state.sourceId;
  }
  function cancelCurrent() {
    clearMarkers();
    if (!current) return;
    clearTimeout(current.timer);
    if (current.busy) { setBusy(current, false); showProgress(current, "paused"); }
    current.section.remove();
    for (const control of current.controls || []) control.remove();
    current = null; sequence++;
  }
  function removeBindings() { for (const binding of bindings.values()) binding.host.remove(); bindings.clear(); }
  function say(state, text, error = false) {
    if (!valid(state)) return;
    state.get("status").textContent = text; state.get("status").className = error ? "status error" : "status";
  }
  function setBusy(state, busy) {
    state.busy = busy;
    state.section.setAttribute("data-busy", String(busy));
    state.get("generate").setAttribute("aria-busy", String(busy));
    for (const name of ["generate", "architecture", "context", "runtime", "target", "new"]) state.get(name).disabled = busy;
    state.get("generate").textContent = busy ? "Gerando sugestão…" : state.submitted && !state.imported ? "Tentar novamente" : state.imported ? "Atualizar resposta" : "Gerar sugestão";
  }
  const terminalStatuses = new Set(["completed", "failed", "cancelled", "human_review_required"]);
  function runFinished(run) { return run.finished === true || terminalStatuses.has(run.status); }
  function runFailed(run) { return run.status !== "cancelled" && (run.status === "failed" || Boolean(run.error)); }
  function progressRows(state) {
    const planned = state.expectedArchitectures || [];
    if (!state.progress) return planned.map((architecture, index) => ({ id: state.imported?.runIds?.[index] || `expected-${index}`, name: core.architectureNames[architecture] || "Arquitetura", status: "waiting", finished: false }));
    return state.progress.runs.map((run) => ({ ...run, name: run.name || core.architectureNames[run.architecture] || "Aguardando execução" }));
  }
  function runLabel(run) {
    if (run.status === "cancelled") return "Cancelada";
    if (runFailed(run)) return "Falhou";
    if (runFinished(run) && !run.text && (run.status === "human_review_required" || run.reviewRequired)) return "Revisão profissional · sem resposta";
    if (runFinished(run) && !run.text) return "Finalizada sem resposta";
    if (run.status === "human_review_required" || (runFinished(run) && run.reviewRequired)) return "Revisão profissional";
    if (runFinished(run)) return "Concluída";
    if (run.status === "running") return "Em execução";
    if (run.status === "pending" && run.architecture) return "Na fila";
    return "Aguardando";
  }
  function showProgress(state, phase) {
    state.phase = phase;
    const region = state.get("progress"), rows = progressRows(state);
    const finished = rows.filter(runFinished).length;
    const available = rows.filter((run) => runFinished(run) && run.text && !runFailed(run) && run.status !== "cancelled").length;
    const failed = rows.filter(runFailed).length, cancelled = rows.filter((run) => run.status === "cancelled").length;
    const empty = rows.filter((run) => runFinished(run) && !run.text && !runFailed(run) && run.status !== "cancelled").length;
    const titles = { sending: "Enviando trecho", running: "Processando no MAB", complete: available && !failed && !cancelled && !empty ? "Respostas disponíveis" : "Processamento encerrado", error: "Não foi possível atualizar", paused: "Acompanhamento pausado" };
    const summary = [`${finished} de ${rows.length} finalizadas`];
    if (available || phase === "complete") summary.push(`${available} resposta${available === 1 ? "" : "s"} ${available === 1 ? "disponível" : "disponíveis"}`);
    if (failed) summary.push(`${failed} falha${failed === 1 ? "" : "s"}`);
    if (cancelled) summary.push(`${cancelled} cancelada${cancelled === 1 ? "" : "s"}`);
    if (empty) summary.push(`${empty} sem resposta`);
    if (phase === "paused" || phase === "error") summary.push(state.progress ? "Último estado recebido; retome pelo botão de geração" : "Sem confirmação de execução; tente novamente");
    const items = rows.map((run) => ({ id: run.id, name: run.name, status: run.status || (runFinished(run) ? "completed" : "waiting"), label: runLabel(run) }));
    const key = JSON.stringify([phase, titles[phase], summary, items]);
    if (state.progressRenderKey === key && !region.hidden) return;
    state.progressRenderKey = key;
    region.hidden = false; region.setAttribute("data-phase", phase);
    state.get("progress-title").textContent = titles[phase];
    state.get("progress-summary").textContent = summary.join(" · ");
    state.get("progress-runs").replaceChildren();
    for (const run of items) {
      const item = document.createElement("li"); item.setAttribute("data-run-id", run.id); item.setAttribute("data-state", run.status);
      const name = document.createElement("span"), badge = document.createElement("span"); name.textContent = run.name; badge.className = "run-state"; badge.textContent = run.label;
      item.append(name, badge); state.get("progress-runs").append(item);
    }
  }
  function resetProgress(state) {
    state.phase = null; state.expectedArchitectures = []; state.progressRenderKey = null;
    state.get("progress").hidden = true; state.get("progress").removeAttribute("data-phase");
    state.get("progress-title").textContent = ""; state.get("progress-summary").textContent = ""; state.get("progress-runs").replaceChildren();
  }
  function selectedCapture(state) {
    if (!valid(state)) throw new Error("A conversa ou a mensagem mudou. Abra a ação novamente.");
    return core.selectContext(state.capture, state.sourceId, state.get("context").value, state.get("target").value);
  }
  function clearMarkers() {
    for (const marker of markers.values()) marker.host.remove();
    markers.clear();
  }
  function markContext(state) {
    if (!valid(state)) { clearMarkers(); return; }
    const selected = selectedCapture(state);
    const rows = new Map([...state.chat.main.querySelectorAll("[data-id]")].filter((row) => !row.closest("[data-mab-ui]")).map((row) => [row.getAttribute("data-id"), row]));
    const desired = new Map(selected.messages.filter((message) => rows.has(message.sourceId)).map((message) => [message.sourceId, message]));
    for (const [id, marker] of markers) if (!desired.has(id) || marker.row !== rows.get(id) || !marker.row.contains(marker.host)) { marker.host.remove(); markers.delete(id); }
    const original = state.capture.messages.find((message) => message.sourceId === state.sourceId)?.text || "";
    const edited = state.get("target").value.trim() !== original.trim();
    for (const [id, message] of desired) {
      const isTarget = id === state.sourceId, row = rows.get(id);
      let marker = markers.get(id);
      if (!marker) {
        const host = document.createElement("div"); host.setAttribute("data-mab-ui", "context-marker"); host.setAttribute("data-mab-source", id);
        host.style.cssText = `display:block;max-width:calc(100% - 80px);margin:4px ${message.role === "attendant" ? "62px 6px auto" : "12px 6px 62px"};text-align:${message.role === "attendant" ? "right" : "left"};clear:both;`;
        const shadow = host.attachShadow({ mode: "open" }), style = document.createElement("style"), label = document.createElement("span");
        style.textContent = `:host{all:initial;display:block}span{display:inline-block;padding:3px 8px;border:1px solid var(--border-default,#b5d6c3);border-radius:5px;background:var(--outgoing-background,#e7f3eb);color:var(--primary,#28573d);font:10px/1.4 system-ui,-apple-system,sans-serif}.target{border:2px solid #3a9b72;font-weight:650}`;
        shadow.append(style, label);
        const actionHost = bindings.get(id)?.host;
        if (actionHost?.parentElement === row) row.insertBefore(host, actionHost); else row.append(host);
        marker = { host, row, label }; markers.set(id, marker);
      }
      const kind = isTarget ? "target" : "context", className = isTarget ? "target" : "";
      const text = isTarget ? `✓ Solicitação selecionada${edited ? " · Texto ajustado no MAB" : ""}` : "✓ Será enviada · contexto";
      if (marker.host.getAttribute("data-mab-context") !== kind) marker.host.setAttribute("data-mab-context", kind);
      if (marker.label.className !== className) marker.label.className = className;
      if (marker.label.textContent !== text) marker.label.textContent = text;
    }
    const legend = `${selected.messages.length} mensagem${selected.messages.length === 1 ? "" : "s"} no trecho · ${desired.size} marcada${desired.size === 1 ? "" : "s"} na conversa.${edited ? " A solicitação usará o texto ajustado no MAB." : " O marcador destacado identifica a solicitação."}`;
    if (state.get("marker-legend").textContent !== legend) state.get("marker-legend").textContent = legend;
  }
  function renderContext(state) {
    try {
      const selected = selectedCapture(state);
      state.get("count").textContent = `${selected.messages.length} mensagem${selected.messages.length === 1 ? "" : "s"} até esta solicitação`;
      state.get("preview").replaceChildren();
      for (const message of selected.messages) {
        const line = document.createElement("p"); line.textContent = `${message.role === "customer" ? "Cliente" : message.role === "attendant" ? "Atendente" : "Participante não identificado"}: ${message.text}`;
        state.get("preview").append(line);
      }
      markContext(state);
    } catch (error) { say(state, error.message, true); }
  }
  function renderResponse(state, progress) {
    state.progress = progress;
    if (!progress.runs.some((run) => run.id === state.activeRun)) state.activeRun = progress.runs[0]?.id;
    state.get("results").hidden = false; state.get("tabs").replaceChildren();
    for (const run of progress.runs) {
      const button = document.createElement("button"); button.type = "button"; button.className = `tab ${run.id === state.activeRun ? "selected" : ""}`;
      button.setAttribute("role", "tab"); button.setAttribute("aria-selected", String(run.id === state.activeRun)); button.textContent = run.name;
      button.addEventListener("click", () => { state.activeRun = run.id; renderResponse(state, state.progress); });
      state.get("tabs").append(button);
    }
    const run = progress.runs.find((item) => item.id === state.activeRun);
    state.get("response").textContent = run?.text || run?.error || (run?.finished ? "Esta execução terminou sem texto disponível." : "Aguardando esta arquitetura…");
    state.get("metrics").textContent = [run?.status === "cancelled" ? "Execução cancelada" : run?.error || run?.status === "failed" ? "Falha na execução" : run?.finished && !run?.text ? run?.reviewRequired || run?.status === "human_review_required" ? "Revisão profissional · sem resposta" : "Finalizada sem resposta" : run?.reviewRequired ? "Revisão profissional indicada" : run?.finished ? "Sugestão pronta" : "Processando", run?.durationMs != null ? `${(run.durationMs / 1000).toFixed(1)} s` : "", run?.tokens != null ? `${run.tokens.toLocaleString("pt-BR")} tokens` : ""].filter(Boolean).join(" · ");
    state.get("copy").disabled = !run?.text;
    state.get("insert").disabled = !run?.text || !run.finished || Boolean(run.error);
  }
  async function poll(state, token, started = Date.now()) {
    if (!valid(state) || token !== sequence) return;
    try {
      const progress = await rpc("mab:progress", { conversationId: state.imported.conversationId, runIds: state.imported.runIds });
      if (!valid(state) || token !== sequence) return;
      renderResponse(state, progress);
      if (progress.finished) { setBusy(state, false); showProgress(state, "complete"); say(state, "Confira os resultados de cada arquitetura. Nada foi enviado ao WhatsApp."); return; }
      if (Date.now() - started > 180000) { setBusy(state, false); showProgress(state, "paused"); say(state, "O MAB pode continuar processando. Use ‘Atualizar resposta’ para retomar o acompanhamento.", true); return; }
      showProgress(state, "running"); say(state, "");
      state.timer = setTimeout(() => void poll(state, token, started), 1800);
    } catch (error) { if (valid(state) && token === sequence) { setBusy(state, false); showProgress(state, "error"); say(state, `${error.message} Tente novamente para retomar.`, true); } }
  }
  async function generate(state) {
    if (state.busy || !valid(state)) return;
    const token = ++sequence;
    try {
      const capture = selectedCapture(state);
      const choices = { targetSourceId: state.sourceId, architectureMode: state.get("architecture").value, runtimeMode: state.get("runtime").value };
      const fingerprint = JSON.stringify({ capture, choices });
      if (state.submitted && fingerprint !== state.submitted) throw new Error("O trecho ou as opções mudaram. Use ‘Nova sugestão’ antes de gerar outra resposta.");
      state.expectedArchitectures = choices.architectureMode === "all_architectures" ? Object.keys(core.architectureNames) : [choices.architectureMode || "centralized_orchestration"];
      state.submitted = fingerprint; state.get("new").hidden = false; setBusy(state, true);
      showProgress(state, state.imported ? "running" : "sending"); say(state, "");
      if (!state.imported) {
        const imported = await rpc("mab:import", { capture, choices });
        if (!valid(state) || token !== sequence) return;
        state.imported = imported;
      }
      showProgress(state, "running");
      await poll(state, token);
    } catch (error) { if (valid(state) && token === sequence) { setBusy(state, false); showProgress(state, "error"); say(state, error.message, true); } }
  }
  function open(binding) {
    if (!sameChat(binding.chat, chat())) { scan(); return; }
    if (current?.sourceId === binding.sourceId && valid(current)) { cancelCurrent(); return; }
    cancelCurrent();
    try {
      binding.shadow.querySelector(".action-error")?.remove();
      const cached = drafts.get(binding.sourceId);
      if (cached && sameChat(cached.chat, chat())) {
        cached.row = binding.row; current = cached;
        for (const control of cached.controls) binding.host.append(control);
        binding.shadow.append(cached.section); setBusy(cached, false); renderContext(cached);
        if (cached.imported && !cached.progress?.finished) { setBusy(cached, true); showProgress(cached, "running"); void poll(cached, ++sequence); }
        else say(cached, cached.imported ? "Sugestão preservada. Use ‘Nova sugestão’ para gerar outra execução." : cached.submitted ? "Tentativa preservada. Tente novamente para recuperar a mesma importação." : "Trecho preservado. Confira o contexto antes de gerar.");
        return;
      }
      const capture = { ...globalThis.MabWhatsAppCapture.captureWhatsApp(), captureId: crypto.randomUUID() };
      const target = capture.messages.find((message) => message.sourceId === binding.sourceId && message.role === "customer");
      if (!target || binding.row.getAttribute("data-id") !== binding.sourceId) return;
      const section = document.createElement("section"); section.className = "suggestion"; section.setAttribute("aria-label", "Sugestão MAB para esta mensagem"); section.setAttribute("data-busy", "false");
      section.innerHTML = `<div class="card-head"><strong>Sugestão de resposta</strong><button id="close" class="quiet" type="button" aria-label="Fechar sugestão">×</button></div><div class="choices"><label>Arquitetura<select id="architecture" aria-label="Arquitetura"><option value="centralized_orchestration">Centralizada</option><option value="structured_workflow">Workflow</option><option value="decentralized_swarm">Swarm</option><option value="all_architectures">Comparar as três</option></select></label><label>Contexto<select id="context" aria-label="Contexto"><option value="recent">Últimas 10 mensagens</option><option value="target">Só esta solicitação</option></select></label></div><p id="count" class="small"></p><p id="marker-legend" class="small" aria-live="polite"></p><details><summary>Ajustar solicitação e conferir contexto</summary><textarea id="target" rows="2" aria-label="Ajustar solicitação"></textarea><div id="preview" class="preview"></div><label class="mode">Execução<select id="runtime" aria-label="Execução"><option value="real">Real · Bedrock</option><option value="mock">Simulada · sem modelo</option></select></label><button id="settings" class="link" type="button">Configurar conexão local</button></details><p class="small">Fontes controladas; mídias não são lidas. O modo real envia o trecho ao modelo.</p><button id="generate" class="primary" type="button" aria-busy="false">Gerar sugestão</button><div id="progress" class="progress" role="region" aria-label="Progresso da sugestão" aria-live="polite" hidden><div class="progress-heading"><span class="progress-spinner" aria-hidden="true"></span><strong id="progress-title"></strong></div><p id="progress-summary" class="small"></p><ul id="progress-runs"></ul></div><p id="status" class="status" role="status" aria-live="polite"></p><div id="results" hidden><div id="tabs" class="tabs" role="tablist" aria-label="Respostas por arquitetura"></div><p id="metrics" class="small"></p><div id="response" class="response" role="tabpanel" tabindex="0"></div><div class="result-actions"><button id="insert" class="primary" type="button" disabled>Inserir na conversa</button><button id="copy" class="secondary" type="button" disabled>Copiar resposta</button><button id="details" class="link" type="button">Detalhes no MAB ↗</button></div><p class="small">A inserção preenche o rascunho. Revise e envie pelo WhatsApp.</p></div><button id="new" class="link" type="button" hidden>Nova sugestão</button>`;
      // Keep native editors in light DOM, projected into the isolated card. This
      // lets WhatsApp's global handlers see the real textarea/select instead of
      // a retargeted, non-editable Shadow DOM host and stealing typing focus.
      const controls = [...section.querySelectorAll("textarea, select, input")];
      const isolatedEvents = ["pointerdown", "mousedown", "click", "focus", "focusin", "blur", "focusout", "keydown", "keypress", "keyup", "beforeinput", "input", "compositionstart", "compositionupdate", "compositionend", "paste", "copy", "cut"];
      for (const control of controls) {
        const id = control.id, slot = document.createElement("slot");
        slot.name = `mab-${id}`; control.setAttribute("slot", slot.name); control.setAttribute("data-mab-control", id); control.removeAttribute("id");
        control.replaceWith(slot); binding.host.append(control);
        // Preserve native editing/selection/composition defaults. Only suppress
        // propagation into the surrounding chat's global focus/key handlers.
        for (const name of isolatedEvents) control.addEventListener(name, (event) => event.stopPropagation());
      }
      binding.shadow.append(section);
      const state = { sourceId: binding.sourceId, row: binding.row, section, controls, capture, chat: chat(), get(id) { return this.controls.find((control) => control.getAttribute("data-mab-control") === id) || this.section.querySelector(`#${id}`); }, busy: false, imported: null, submitted: null };
      current = state; state.get("target").value = target.text;
      drafts.set(binding.sourceId, state);
      if (drafts.size > 10) drafts.delete(drafts.keys().next().value);
      state.get("close").addEventListener("click", cancelCurrent);
      state.get("context").addEventListener("change", () => renderContext(state)); state.get("target").addEventListener("input", () => renderContext(state));
      state.get("generate").addEventListener("click", (event) => { if (event.isTrusted) void generate(state); });
      state.get("new").addEventListener("click", (event) => { if (!event.isTrusted || !valid(state)) return; clearTimeout(state.timer); sequence++; state.capture.captureId = crypto.randomUUID(); state.imported = null; state.submitted = null; state.progress = null; resetProgress(state); state.get("new").hidden = true; state.get("results").hidden = true; setBusy(state, false); say(state, "Pronto para uma nova execução deste trecho."); });
      state.get("copy").addEventListener("click", async (event) => { if (!event.isTrusted || !valid(state)) return; const run = state.progress?.runs.find((item) => item.id === state.activeRun); if (!run?.text) return; try { await navigator.clipboard.writeText(run.text); say(state, "Resposta copiada. Revise e cole quando desejar."); } catch { say(state, "Selecione o texto da sugestão para copiar manualmente.", true); } });
      state.get("insert").addEventListener("click", (event) => {
        if (!event.isTrusted || !valid(state)) return;
        const run = state.progress?.runs.find((item) => item.id === state.activeRun);
        if (!run?.text || !run.finished || run.error) return;
        try {
          const result = globalThis.MabWhatsAppComposer.insertReply({ main: state.chat.main, isCurrent: () => valid(state), text: run.text });
          say(state, result.appended ? "Sugestão acrescentada ao rascunho existente. Revise e envie pelo WhatsApp quando desejar." : "Sugestão inserida na caixa de mensagem. Revise e envie pelo WhatsApp quando desejar.");
        } catch (error) { say(state, error.message || "Não foi possível inserir a sugestão. Use Copiar resposta.", true); }
      });
      state.get("details").addEventListener("click", (event) => { if (event.isTrusted && valid(state) && state.imported) void rpc("mab:open-details", { conversationId: state.imported.conversationId }).catch((error) => say(state, error.message, true)); });
      state.get("settings").addEventListener("click", (event) => { if (event.isTrusted) void rpc("mab:open-settings").catch((error) => say(state, error.message, true)); });
      renderContext(state); say(state, "Confira o contexto e clique em Gerar sugestão.");
    } catch (error) {
      if (!binding.row.isConnected || binding.row.getAttribute("data-id") !== binding.sourceId) return;
      const notice = document.createElement("p"); notice.className = "status error action-error"; notice.setAttribute("role", "alert");
      notice.textContent = error.message || "Não foi possível preparar esta mensagem. Atualize a conversa e tente novamente."; binding.shadow.append(notice);
    }
  }
  const css = `:host{all:initial;display:block;font:12px/1.45 system-ui,-apple-system,sans-serif;color:var(--primary,#244b3b);color-scheme:light dark}*{box-sizing:border-box}[hidden]{display:none!important}button,select,textarea{font:inherit}button{cursor:pointer}button:disabled{opacity:.5;cursor:default}button:focus-visible,select:focus-visible,textarea:focus-visible,summary:focus-visible{outline:2px solid #53ad86;outline-offset:2px}::slotted(select),::slotted(textarea){box-sizing:border-box;display:block;width:100%;border:1px solid var(--border-default,#d4e1d8);border-radius:6px;background:var(--incoming-background,#fff);color:var(--primary,#244b3b);padding:7px;margin-top:3px;font:11px/1.45 system-ui,-apple-system,sans-serif}::slotted(textarea){resize:vertical;min-height:55px}::slotted(:focus-visible){outline:2px solid #53ad86;outline-offset:2px}.action{border:0;background:transparent;color:var(--secondary,#63806f);font:600 11px system-ui;padding:4px 2px;opacity:.9}.action:hover{color:#268363;text-decoration:underline}.suggestion{margin-top:4px;padding:12px 13px;border-radius:9px;border:1px solid var(--border-default,#d8e5dc);border-left:3px solid #4b9f7a;background:var(--incoming-background,#fff);color:var(--primary,#244b3b);box-shadow:0 1px 2px #14271a0a}.card-head{display:flex;justify-content:space-between;align-items:center;font-size:12px}.quiet{border:0;background:transparent;color:inherit;font-size:18px;padding:0 3px}.choices{display:flex;gap:10px;margin-top:10px}.choices label{flex:1;min-width:0;font-size:10px;color:var(--secondary,#63806f)}select,textarea{display:block;width:100%;border:1px solid var(--border-default,#d4e1d8);border-radius:6px;background:var(--incoming-background,#fff);color:var(--primary,#244b3b);padding:7px;margin-top:3px;font-size:11px}textarea{resize:vertical;min-height:55px}.small{font-size:10px;color:var(--secondary,#6c8275);margin:7px 0}.primary,.secondary{border:0;border-radius:6px;background:#287658;color:#fff;padding:8px 12px;font-size:11px;font-weight:650}.secondary{background:var(--incoming-background,#fff);color:var(--primary,#2e654d);border:1px solid var(--border-default,#d3e2d7);padding:6px 10px}.link{border:0;background:transparent;color:#318668;padding:3px 0;font-size:10px;text-decoration:underline;text-underline-offset:2px}.status{font-size:11px;color:var(--secondary,#4e795f);margin:8px 0;white-space:pre-wrap}.error{color:#bd5f45}details{font-size:10px;color:var(--secondary,#64806d);margin:7px 0}summary{cursor:pointer}.preview{max-height:170px;overflow:auto;font-size:10px}.preview p{white-space:pre-wrap;border-left:2px solid #a7cbb5;padding-left:7px}.mode{display:block;margin:7px 0}.tabs{display:flex;gap:4px;margin-top:10px}.tab{flex:1;border:1px solid var(--border-default,#d3e1d6);border-radius:5px;background:transparent;color:inherit;padding:6px 3px;font-size:10px}.selected{background:#dceee3;color:#255c3e;font-weight:700}.response{max-height:260px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.5 system-ui}.result-actions{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:9px}`;
  const progressCss = `.progress{border:1px solid var(--border-default,#d5e4d9);border-radius:7px;padding:9px 10px;margin-top:10px;background:var(--incoming-background,#fff)}.progress-heading{display:flex;align-items:center;gap:8px;font-size:11px}.progress-spinner{display:none;width:12px;height:12px;border:2px solid var(--border-default,#bcd2c2);border-top-color:#3a9b72;border-radius:50%;animation:mab-progress-spin .9s linear infinite}.progress[data-phase="sending"] .progress-spinner,.progress[data-phase="running"] .progress-spinner{display:inline-block}#progress-runs{list-style:none;padding:0;margin:7px 0 0;font-size:10px}#progress-runs li{display:flex;justify-content:space-between;gap:12px;padding:3px 0}.run-state{font-weight:600;text-align:right}#progress-runs li[data-state="failed"] .run-state{color:#bd5f45}#progress-runs li[data-state="cancelled"] .run-state{color:var(--secondary,#6b8072)}.progress[data-phase="error"]{border-color:#b56851}.progress[data-phase="paused"]{border-style:dashed}@keyframes mab-progress-spin{to{transform:rotate(360deg)}}@media(prefers-reduced-motion:reduce){.progress-spinner{animation:none}}`;
  function bind(message, row) {
    const host = document.createElement("div"); host.setAttribute("data-mab-ui", "message-action"); host.className = "mab-message-action";
    host.style.cssText = "display:block;max-width:min(440px,calc(100% - 80px));margin:3px 12px 7px 62px;clear:both;";
    const shadow = host.attachShadow({ mode: "open" }); const style = document.createElement("style"); style.textContent = css + progressCss;
    const action = document.createElement("button"); action.type = "button"; action.className = "action"; action.textContent = "Sugerir resposta · MAB";
    action.setAttribute("aria-label", "Sugerir resposta com MAB para esta mensagem");
    const binding = { sourceId: message.sourceId, row, host, shadow, chat: chat() };
    action.addEventListener("click", (event) => { if (event.isTrusted) open(binding); }); shadow.append(style, action); row.append(host); bindings.set(message.sourceId, binding);
  }
  function scan() {
    if (!enabled) return;
    const now = chat();
    if (!sameChat(activeChat, now)) { cancelCurrent(); removeBindings(); drafts.clear(); activeChat = now; }
    if (current && !valid(current)) cancelCurrent();
    if (current) markContext(current);
    for (const [id, binding] of bindings) if (!now.main?.contains(binding.row) || binding.row.getAttribute("data-id") !== id || !binding.row.contains(binding.host)) { binding.host.remove(); bindings.delete(id); }
    if (!now.main) return;
    try {
      const capture = globalThis.MabWhatsAppCapture.captureWhatsApp();
      const eligible = new Set(capture.messages.filter((message) => message.role === "customer" && !/^\[Anexo presente no WhatsApp\./.test(message.text)).map((message) => message.sourceId));
      for (const [id, binding] of bindings) if (!eligible.has(id)) { if (current?.sourceId === id) cancelCurrent(); binding.host.remove(); bindings.delete(id); }
      const rows = new Map([...now.main.querySelectorAll("[data-id]")].filter((row) => !row.closest("[data-mab-ui]")).map((row) => [row.getAttribute("data-id"), row]));
      for (const message of capture.messages) {
        if (message.role !== "customer" || /^\[Anexo presente no WhatsApp\./.test(message.text)) continue;
        const row = rows.get(message.sourceId); if (row && !bindings.has(message.sourceId)) bind(message, row);
      }
    } catch { /* Empty/loading conversations simply have no actions. */ }
  }
  function ownedNode(node) {
    const element = node?.nodeType === 1 ? node : node?.parentElement;
    if (element?.closest?.("[data-mab-ui]")) return true;
    return Boolean(element?.getRootNode?.().host?.closest?.("[data-mab-ui]"));
  }
  function scheduleScan(records = []) {
    // Marker/control changes are extension UI, not new chat content. Ignore
    // them so our own rendering never feeds a MutationObserver scan loop.
    if (records.length && !records.some((record) => {
      if (ownedNode(record.target)) return false;
      if (record.type === "childList") {
        const changed = [...record.addedNodes, ...record.removedNodes];
        if (changed.length && changed.every(ownedNode)) return false;
      }
      return true;
    })) return;
    if (current && !valid(current)) cancelCurrent();
    clearTimeout(scanTimer); scanTimer = setTimeout(scan, 60);
  }
  function enable() {
    document.getElementById("mab-whatsapp-assistant")?.remove();
    // Reloading the extension can leave DOM from an invalidated old isolated
    // context. Remove only our previous action hosts before mounting new ones.
    for (const host of document.querySelectorAll("#main [data-mab-ui='message-action']")) host.remove();
    enabled = true; activeChat = chat(); scan();
    observer = new MutationObserver(scheduleScan); observer.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ["aria-label", "data-id"] });
    document.addEventListener("pointerdown", onSidebar, true);
  }
  function onSidebar(event) { if (!activeChat?.main?.contains(event.target) && event.target.closest?.("[role='row'], [data-testid='cell-frame-container']")) cancelCurrent(); }
  function disable() { enabled = false; clearTimeout(scanTimer); observer?.disconnect(); document.removeEventListener("pointerdown", onSidebar, true); cancelCurrent(); removeBindings(); drafts.clear(); activeChat = null; }
  globalThis.MabWhatsAppMessages = { toggle() { if (enabled) disable(); else enable(); return { enabled, actions: bindings.size }; } };
})();
