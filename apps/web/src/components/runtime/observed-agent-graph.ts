import type { RunExecutionEvent } from "@/lib/types";

/** A role appears only after a recorded agent invocation, never from a tool name. */
export function observedAgentGraph(events: RunExecutionEvent[], terminal: boolean) {
  const ordered = [...events].sort((a, b) => a.sequenceNo - b.sequenceNo);
  const invocations = new Map<string, string>();
  const roles = new Map<string, { role: string; status: string; events: RunExecutionEvent[] }>();
  for (const event of ordered) {
    if (event.eventFamily !== "agent" || !event.actorName) continue;
    const payload = event.payload ?? {};
    const invocationId = payload.agentInvocationId ?? payload.callId;
    if (typeof invocationId === "string") invocations.set(invocationId, event.actorName);
    if (event.eventName === "started") {
      roles.set(event.actorName, { role: event.actorName, status: event.status, events: [] });
    }
  }
  for (const [role, entry] of roles) {
    entry.events = ordered.filter((event) => event.actorName === role);
    const lastAgentEvent = entry.events.filter((event) => event.eventFamily === "agent").at(-1);
    entry.status = lastAgentEvent?.status ?? entry.status;
    if (terminal && entry.status === "running") entry.status = "interrupted";
  }

  const links = new Map<string, { from: string; to: string; kind: "call" | "return"; status: string }>();
  for (const event of ordered) {
    const payload = event.payload ?? {};
    if (event.eventFamily === "agent" && event.eventName === "started" && event.actorName) {
      const parentId = payload.parentAgentInvocationId;
      const parentRole = typeof parentId === "string" ? invocations.get(parentId) : undefined;
      if (parentRole && roles.has(parentRole) && parentRole !== event.actorName) {
        links.set(`${parentRole}:${event.actorName}:call`, {
          from: parentRole, to: event.actorName, kind: "call", status: event.status,
        });
      }
    }
    if (event.eventFamily === "communication" && event.eventName === "message" && event.actorName) {
      const to = payload.to;
      if (typeof to === "string" && roles.has(event.actorName) && roles.has(to) && event.actorName !== to) {
        links.set(`${event.actorName}:${to}:return`, {
          from: event.actorName, to, kind: "return", status: event.status,
        });
      }
    }
  }
  return { agents: [...roles.values()], links: [...links.values()] };
}
