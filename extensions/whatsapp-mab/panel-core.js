// Shared, dependency-free state rules. No WhatsApp internals or credentials.
(() => {
  const terminal = new Set(["completed", "failed", "cancelled", "human_review_required"]);
  const names = { centralized_orchestration: "Centralizada", structured_workflow: "Workflow", decentralized_swarm: "Swarm" };
  function selectContext(capture, targetSourceId, mode = "recent", text) {
    const index = capture.messages.findIndex((message) => message.sourceId === targetSourceId);
    if (index < 0 || capture.messages[index].role !== "customer") throw new Error("Escolha uma mensagem recebida do cliente.");
    const start = mode === "target" ? index : Math.max(0, index - 9);
    const messages = capture.messages.slice(start, index + 1).map((message) => ({ ...message, included: true }));
    if (text !== undefined) messages[messages.length - 1].text = text;
    return { ...capture, messages, targetSourceId };
  }
  function latestCustomer(capture) { return [...capture.messages].reverse().find((message) => message.role === "customer") || null; }
  function summarizeRuns(data, ids) {
    if (!Array.isArray(ids) || !ids.length) throw new Error("A importação não informou as execuções.");
    const runs = ids.map((id) => {
      const run = (data.runs || []).find((item) => item.id === id);
      if (!run) return { id, status: "pending", architecture: "", name: "Aguardando execução", text: "", finished: false };
      const message = (data.messages || []).find((item) => item.direction === "outbound" && item.metadata?.importedHistory !== true && item.metadata?.runtimeRunId === id);
      const architecture = run.experiment?.architectureKey || "";
      const failed = ["failed", "cancelled"].includes(run.status);
      return { id, architecture, name: names[architecture] || architecture || "Arquitetura", status: run.status,
        text: failed ? "" : message?.contentText || "", finished: terminal.has(run.status),
        error: failed ? String(run.summary?.stopReason || run.finalOutcome || "A execução não produziu uma resposta.").slice(0, 350) : null,
        durationMs: run.totalDurationMs ?? null, tokens: run.summary?.totalTokens ?? null,
        reviewRequired: run.status === "human_review_required" || run.humanReviewRequired === true };
    });
    return { runs, finished: runs.every((run) => run.finished), ready: runs.filter((run) => run.text).length };
  }
  globalThis.MabPanelCore = { selectContext, latestCustomer, summarizeRuns, architectureNames: names };
})();
