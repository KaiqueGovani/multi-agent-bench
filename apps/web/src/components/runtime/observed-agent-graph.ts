import type { RunExecutionEvent } from "@/lib/types";

/** A role appears only after a recorded agent invocation, never from a tool name. */
export function observedAgentGraph(events: RunExecutionEvent[], terminal: boolean) {
  const ordered = [...events].sort((a, b) => a.sequenceNo - b.sequenceNo);
  const invocations = new Map<string, { role: string; status: string }>();
  const roles = new Map<string, { role: string; status: string; events: RunExecutionEvent[] }>();
  for (const event of ordered) {
    if (event.eventFamily !== "agent" || !event.actorName) continue;
    const payload = event.payload ?? {};
    const invocationId = payload.agentInvocationId ?? payload.callId;
    if (typeof invocationId === "string" && (event.eventName === "started" || invocations.has(invocationId))) {
      invocations.set(invocationId, { role: event.actorName, status: event.status });
    }
    if (event.eventName === "started" && !roles.has(event.actorName)) {
      roles.set(event.actorName, { role: event.actorName, status: event.status, events: [] });
    }
  }
  const activeRoles = new Set([...invocations.values()].filter(({ status }) => status === "running").map(({ role }) => role));
  for (const [role, entry] of roles) {
    entry.events = ordered.filter((event) => event.actorName === role);
    const lastAgentEvent = entry.events.filter((event) => event.eventFamily === "agent").at(-1);
    entry.status = activeRoles.has(role) ? "running" : lastAgentEvent?.status ?? entry.status;
    if (terminal && entry.status === "running") entry.status = "interrupted";
  }

  const links = new Map<string, { from: string; to: string; kind: "call" | "return"; status: string }>();
  for (const event of ordered) {
    const payload = event.payload ?? {};
    if (event.eventFamily === "agent" && event.eventName === "started" && event.actorName) {
      const parentId = payload.parentAgentInvocationId;
      const parentRole = typeof parentId === "string" ? invocations.get(parentId)?.role : undefined;
      if (parentRole && roles.has(parentRole) && parentRole !== event.actorName) {
        const invocationId = payload.agentInvocationId ?? payload.callId;
        const status = (typeof invocationId === "string" ? invocations.get(invocationId)?.status : undefined) ?? event.status;
        const key = `${parentRole}:${event.actorName}:call`;
        const previous = links.get(key);
        const combined = previous?.status === "running" ? "running" : status;
        links.set(key, {
          from: parentRole, to: event.actorName, kind: "call",
          status: terminal && combined === "running" ? "interrupted" : combined,
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
