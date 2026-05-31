"use client";

import {
  ReactFlow,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
  BaseEdge,
  getBezierPath,
  type EdgeProps,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { memo, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import type { RunExecutionEvent } from "@/lib/types";

// ---------------------------------------------------------------------------
// Shared types
// ---------------------------------------------------------------------------

type EdgeState = "idle" | "recent" | "active" | "settled";

interface AgentNodeData {
  actorName: string;
  description: string;
  status: string;
  statusLabel?: string;
  active: boolean;
  tone?: BadgeProps["variant"];
  nodeId?: string | null;
  events?: RunExecutionEvent[];
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Agent event detail popover
// ---------------------------------------------------------------------------

function AgentEventTimeline({ events }: { events: RunExecutionEvent[] }) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (events.length === 0) {
    return (
      <p className="px-2 py-1.5 text-[11px] text-muted-foreground">
        Nenhum evento registrado.
      </p>
    );
  }

  return (
    <div className="max-h-64 overflow-y-auto">
      {events.map((event) => {
        const isExpanded = expandedId === event.id;
        const hasDetail = event.eventFamily === "tool" || event.eventFamily === "response";
        const payload = event.payload as Record<string, unknown> | undefined;

        return (
          <div key={event.id} className="border-b border-border/50 last:border-0">
            <button
              type="button"
              className="flex w-full items-center gap-2 px-2 py-1.5 text-left text-[11px] transition-colors hover:bg-muted/50"
              onClick={(e) => {
                e.stopPropagation();
                if (hasDetail) setExpandedId(isExpanded ? null : event.id);
              }}
            >
              <EventDot family={event.eventFamily} status={event.status} />
              <span className="min-w-0 flex-1 truncate font-medium">
                {event.eventFamily}.{event.eventName}
              </span>
              {event.toolName ? (
                <Badge variant="outline" className="text-[9px] px-1 py-0">
                  {formatToolLabel(event.toolName)}
                </Badge>
              ) : null}
              <span className="shrink-0 text-muted-foreground">
                {event.durationMs ? `${event.durationMs}ms` : ""}
              </span>
              {hasDetail ? (
                <span className={`text-muted-foreground transition-transform ${isExpanded ? "rotate-90" : ""}`}>
                  ›
                </span>
              ) : null}
            </button>
            {isExpanded && hasDetail ? (
              <div className="border-t border-dashed bg-muted/20 px-3 py-2 text-[11px]">
                {event.eventFamily === "tool" ? (
                  <ToolCallDetail payload={payload} eventName={event.eventName} />
                ) : event.eventFamily === "response" ? (
                  <ResponseDetail payload={payload} />
                ) : null}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function EventDot({ family, status }: { family: string; status: string }) {
  const color =
    status === "failed" ? "bg-red-500"
    : status === "running" ? "bg-amber-500"
    : family === "tool" ? "bg-blue-500"
    : family === "handoff" ? "bg-purple-500"
    : family === "response" ? "bg-emerald-500"
    : family === "node" ? "bg-sky-400"
    : "bg-muted-foreground/50";

  return <span className={`h-2 w-2 shrink-0 rounded-full ${color}`} />;
}

function ToolCallDetail({ payload, eventName }: { payload: Record<string, unknown> | undefined; eventName: string }) {
  if (!payload) return <p className="text-muted-foreground">Sem dados.</p>;

  const input = payload.input as Record<string, unknown> | undefined;
  const result = payload.result as Record<string, unknown> | undefined;

  return (
    <div className="space-y-1.5">
      {eventName === "started" && input ? (
        <div>
          <p className="font-medium text-foreground">Entrada:</p>
          <pre className="mt-0.5 max-h-20 overflow-auto rounded bg-background p-1.5 text-[10px] text-muted-foreground">
            {JSON.stringify(input, null, 2)}
          </pre>
        </div>
      ) : null}
      {eventName === "completed" && result ? (
        <div>
          <p className="font-medium text-foreground">Resultado:</p>
          <pre className="mt-0.5 max-h-20 overflow-auto rounded bg-background p-1.5 text-[10px] text-muted-foreground">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      ) : null}
      {!input && !result ? (
        <pre className="max-h-20 overflow-auto rounded bg-background p-1.5 text-[10px] text-muted-foreground">
          {JSON.stringify(payload, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}

function ResponseDetail({ payload }: { payload: Record<string, unknown> | undefined }) {
  if (!payload) return <p className="text-muted-foreground">Sem dados.</p>;
  const contentText = payload.contentText as string | undefined;
  return (
    <div className="space-y-1">
      {contentText ? (
        <p className="max-h-24 overflow-auto whitespace-pre-wrap text-foreground leading-relaxed">
          {contentText.length > 300 ? contentText.slice(0, 300) + "..." : contentText}
        </p>
      ) : (
        <pre className="max-h-20 overflow-auto rounded bg-background p-1.5 text-[10px] text-muted-foreground">
          {JSON.stringify(payload, null, 2)}
        </pre>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Custom node with hover popover
// ---------------------------------------------------------------------------

interface PopoverPosition {
  top: number;
  left: number;
  below: boolean;
}

const POPOVER_WIDTH = 288; // w-72
const POPOVER_DISMISS_MS = 120;

const AgentNode = memo(function AgentNode({ data }: NodeProps<Node<AgentNodeData>>) {
  const { actorName, description, status, statusLabel, active, tone, nodeId, events } = data;
  const [popoverPos, setPopoverPos] = useState<PopoverPosition | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const dismissTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const agentEvents = (events ?? []) as RunExecutionEvent[];
  const eventCount = agentEvents.length;
  const toolCount = agentEvents.filter((e) => e.eventFamily === "tool").length;
  const responseCount = agentEvents.filter((e) => e.eventFamily === "response").length;

  useEffect(() => {
    return () => {
      if (dismissTimer.current) clearTimeout(dismissTimer.current);
    };
  }, []);

  const showPopover = () => {
    if (dismissTimer.current) {
      clearTimeout(dismissTimer.current);
      dismissTimer.current = null;
    }
    if (!cardRef.current || eventCount === 0) return;
    const rect = cardRef.current.getBoundingClientRect();
    const below = rect.bottom + 300 <= window.innerHeight;
    const rawLeft = rect.left + rect.width / 2 - POPOVER_WIDTH / 2;
    const left = Math.max(8, Math.min(rawLeft, window.innerWidth - POPOVER_WIDTH - 8));
    const top = below ? rect.bottom + 6 : rect.top - 6;
    setPopoverPos({ top, left, below });
  };

  const scheduleDismiss = () => {
    dismissTimer.current = setTimeout(() => {
      setPopoverPos(null);
    }, POPOVER_DISMISS_MS);
  };

  const cancelDismiss = () => {
    if (dismissTimer.current) {
      clearTimeout(dismissTimer.current);
      dismissTimer.current = null;
    }
  };

  return (
    <div className="relative">
      <div
        ref={cardRef}
        className={`rounded-2xl border px-4 py-3 shadow-sm transition-colors min-w-[140px] max-w-[180px] ${
          active
            ? "border-primary/60 bg-primary/10 ring-2 ring-primary/20"
            : status === "completed"
              ? "border-emerald-200 bg-emerald-50/80"
              : status === "skipped" || status === "not_invoked" || status === "not_applicable" || tone === "muted"
                ? "border-dashed border-border/70 bg-muted/20"
                : "border-border bg-background"
        }`}
        onMouseEnter={showPopover}
        onMouseLeave={scheduleDismiss}
      >
        <Handle type="target" position={Position.Left} className="!bg-transparent !border-0 !w-0 !h-0" />
        <Handle type="source" position={Position.Right} className="!bg-transparent !border-0 !w-0 !h-0" />
        <div className="flex items-center gap-2">
          <span
            className={`h-2.5 w-2.5 shrink-0 rounded-full ${
              active
                ? "bg-primary animate-pulse"
                : status === "completed"
                  ? "bg-emerald-500"
                  : status === "running"
                    ? "bg-amber-500"
                    : status === "failed"
                      ? "bg-destructive"
                      : status === "skipped"
                        ? "bg-slate-500"
                        : status === "not_applicable"
                          ? "bg-slate-400"
                          : status === "not_invoked"
                            ? "bg-slate-300"
                        : "bg-muted-foreground/50"
            }`}
          />
          <p className="text-sm font-semibold truncate">{actorName}</p>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">{description}</p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Badge variant={tone ?? statusBadgeVariant(status)}>
            {statusLabel ?? formatNodeStatusLabel(status)}
          </Badge>
          {eventCount > 0 ? (
            <span className="text-[10px] text-muted-foreground">
              {toolCount > 0 ? `${toolCount} tool` : ""}
              {toolCount > 0 && responseCount > 0 ? " · " : ""}
              {responseCount > 0 ? `${responseCount} resp` : ""}
              {toolCount === 0 && responseCount === 0 ? `${eventCount} evt` : ""}
            </span>
          ) : null}
        </div>
      </div>

      {popoverPos && eventCount > 0 && typeof document !== "undefined"
        ? createPortal(
            <div
              className="w-72 rounded-lg border bg-card shadow-xl z-[60]"
              style={{
                position: "fixed",
                top: popoverPos.below ? popoverPos.top : undefined,
                bottom: popoverPos.below ? undefined : window.innerHeight - popoverPos.top,
                left: popoverPos.left,
              }}
              onMouseEnter={cancelDismiss}
              onMouseLeave={scheduleDismiss}
            >
              <div className="flex items-center justify-between border-b px-3 py-2">
                <p className="text-xs font-semibold">{actorName}</p>
                <span className="text-[10px] text-muted-foreground">{eventCount} eventos</span>
              </div>
              <AgentEventTimeline events={agentEvents} />
            </div>,
            document.body,
          )
        : null}
    </div>
  );
});

// ---------------------------------------------------------------------------
// Custom animated edge — with handoff coloring
// ---------------------------------------------------------------------------

const EDGE_COLORS: Record<EdgeState, string> = {
  active: "#2563eb",
  recent: "#10b981",
  settled: "#059669",
  idle: "#cbd5e1",
};

function AnimatedEdge(props: EdgeProps) {
  const { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data } = props;
  const state = (data?.state as EdgeState) ?? "idle";

  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const color = EDGE_COLORS[state];
  const strokeWidth = state === "active" ? 2.5 : state === "recent" ? 2 : state === "settled" ? 1.6 : 1;
  const animated = state === "active" || state === "recent";

  return (
    <>
      <BaseEdge
        path={edgePath}
        style={{
          stroke: color,
          strokeWidth,
          opacity: state === "idle" ? 0.3 : 0.9,
        }}
        markerEnd={state !== "idle" ? `url(#marker-${state})` : undefined}
      />
      {animated && (
        <circle r="3.5" fill={color}>
          <animateMotion dur={state === "active" ? "1.2s" : "2s"} repeatCount="indefinite" path={edgePath} />
        </circle>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// SVG marker definitions for edge arrows
// ---------------------------------------------------------------------------

function EdgeMarkerDefs() {
  return (
    <svg className="absolute h-0 w-0">
      <defs>
        {(["active", "recent", "settled"] as EdgeState[]).map((state) => (
          <marker
            key={state}
            id={`marker-${state}`}
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={EDGE_COLORS[state]} />
          </marker>
        ))}
      </defs>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Node & edge type registrations
// ---------------------------------------------------------------------------

const nodeTypes = { agent: AgentNode };
const edgeTypes = { animated: AnimatedEdge };

// ---------------------------------------------------------------------------
// Shared flow wrapper
// ---------------------------------------------------------------------------

function FlowWrapper({
  nodes,
  edges,
  testId,
  height = 340,
}: {
  nodes: Node<AgentNodeData>[];
  edges: Edge[];
  testId: string;
  height?: number;
}) {
  return (
    <div style={{ height }} data-testid={testId} className="relative">
      <EdgeMarkerDefs />
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnDrag={false}
        zoomOnScroll={false}
        zoomOnPinch={false}
        zoomOnDoubleClick={false}
        preventScrolling={false}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const AGENT_NAME_MAP: Record<string, string> = {
  supervisor_agent: "Supervisor",
  faq_agent: "FAQ",
  stock_agent: "Estoque",
  image_intake_agent: "Imagem",
  faq_specialist: "FAQ",
  stock_specialist: "Estoque",
  image_specialist: "Imagem",
  router_agent: "Roteador",
  review_agent: "Revisor",
  synthesis_agent: "Síntese",
  swarm_coordinator: "Par Inicial",
  swarm_synthesizer: "Sintetizador",
  response_streamer: "Resposta",
  workflow_evidence_agent: "Evidências",
  workflow_multimodal_agent: "Multimodal",
  workflow_review_agent: "Revisor",
  workflow_synthesis_agent: "Síntese",
  multi_modal: "Multimodal",
  multi_modal_agent: "Multimodal",
  multimodal_agent: "Multimodal",
};

const TOOL_LABEL_MAP: Record<string, string> = {
  faq_lookup: "FAQ",
  stock_lookup: "Estoque",
  attachment_intake: "Anexo",
  handoff_to_peer: "Handoff",
};

function formatToolLabel(name: string): string {
  return TOOL_LABEL_MAP[name] ?? name;
}

function formatAgentName(name: string): string {
  return AGENT_NAME_MAP[name] ?? name;
}

function statusBadgeVariant(status: string): BadgeProps["variant"] {
  if (status === "completed") return "success";
  if (status === "running") return "warning";
  if (status === "failed" || status === "human_review_required") return "destructive";
  if (status === "skipped") return "outline";
  if (status === "not_invoked" || status === "not_applicable") return "outline";
  if (status === "pending") return "muted";
  return "outline";
}

function getActorName(value: unknown): string | null {
  if (!value || typeof value !== "object") return null;
  const raw = (value as Record<string, unknown>).actorName;
  return typeof raw === "string" ? raw : null;
}

function getStatus(value: unknown, terminal = false): string {
  if (!value || typeof value !== "object") return terminal ? "skipped" : "pending";
  const raw = (value as Record<string, unknown>).status ?? (value as Record<string, unknown>).lastStatus;
  return typeof raw === "string" ? raw : terminal ? "skipped" : "pending";
}

function getNodeId(value: unknown): string | null {
  if (!value || typeof value !== "object") return null;
  const raw = (value as Record<string, unknown>).nodeId;
  return typeof raw === "string" ? raw : null;
}

function getStage(value: unknown): string | null {
  if (!value || typeof value !== "object") return null;
  const raw = (value as Record<string, unknown>).stage;
  return typeof raw === "string" ? raw : null;
}

function getHandoffPairKey(value: unknown): string | null {
  if (!value || typeof value !== "object") return null;
  const payload = (value as Record<string, unknown>).payload;
  if (!payload || typeof payload !== "object") return null;
  const from = (payload as Record<string, unknown>).from;
  const to = (payload as Record<string, unknown>).to;
  return typeof from === "string" && typeof to === "string" ? `${from}->${to}` : null;
}

function groupEventsByActor(events: RunExecutionEvent[]): Map<string, RunExecutionEvent[]> {
  const map = new Map<string, RunExecutionEvent[]>();
  for (const event of events) {
    const actor = event.actorName ?? "runtime";
    const list = map.get(actor) ?? [];
    list.push(event);
    map.set(actor, list);
  }
  return map;
}

function makeNode(
  id: string,
  actorName: string,
  description: string,
  status: string,
  active: boolean,
  x: number,
  y: number,
  tone?: BadgeProps["variant"],
  nodeId?: string | null,
  statusLabel?: string,
  events?: RunExecutionEvent[],
): Node<AgentNodeData> {
  return {
    id,
    type: "agent",
    position: { x, y },
    data: { actorName, description, status, statusLabel, active, tone, nodeId, events: events ?? [] },
  };
}

function makeEdge(source: string, target: string, state: EdgeState): Edge {
  return {
    id: `${source}-${target}`,
    source,
    target,
    type: "animated",
    data: { state },
  };
}

function edgeStateFromEvents(
  events: RunExecutionEvent[],
  source: string,
  target: string,
  terminal = false,
  altNames?: Map<string, string[]>,
): EdgeState {
  const sourceNames = new Set([source, ...(altNames?.get(source) ?? [])]);
  const targetNames = new Set([target, ...(altNames?.get(target) ?? [])]);

  const matchesSource = (name: string) => sourceNames.has(name);
  const matchesTarget = (name: string) => targetNames.has(name);

  // Check recent events for active/recent state
  const recent = events.slice(-12);
  for (let i = recent.length - 1; i >= 0; i--) {
    const e = recent[i];
    const actor = e.actorName;
    if (!actor) continue;

    if (e.eventFamily === "handoff") {
      const p = e.payload as Record<string, unknown>;
      const from = p.from as string | undefined;
      const to = (p.to ?? p.targetActor) as string | undefined;
      if (
        (from && to && matchesSource(from) && matchesTarget(to)) ||
        (matchesSource(actor) && to && matchesTarget(to))
      ) {
        if (e.status === "running") return "active";
        return terminal ? "settled" : "recent";
      }
    }

    if (e.eventFamily === "node" || e.eventFamily === "tool") {
      if (matchesTarget(actor)) {
        if (e.status === "running") return "active";
        if (e.status === "completed") return terminal ? "settled" : "recent";
      }
    }

    if (e.eventFamily === "response" && matchesTarget(actor)) {
      if (e.status === "running") return "active";
      if (e.status === "completed") return terminal ? "settled" : "recent";
    }
  }

  // For terminal runs, check the full event history to see if target was ever active
  if (terminal) {
    const targetHasActivity = events.some((e) =>
      e.actorName && matchesTarget(e.actorName) &&
      (e.eventFamily === "node" || e.eventFamily === "tool" || e.eventFamily === "response") &&
      e.status === "completed"
    );
    const sourceHasActivity = events.some((e) =>
      e.actorName && matchesSource(e.actorName) &&
      (e.eventFamily === "node" || e.eventFamily === "tool" || e.eventFamily === "response" || e.eventFamily === "handoff")
    );
    if (targetHasActivity && sourceHasActivity) return "settled";
    if (targetHasActivity) return "settled";
  }

  return "idle";
}

// ---------------------------------------------------------------------------
// CentralizedFlow
// ---------------------------------------------------------------------------

export function CentralizedFlow({
  activeActorName,
  actors,
  executionEvents,
  runStatus,
}: {
  activeActorName: string;
  actors: unknown[];
  executionEvents: RunExecutionEvent[];
  runStatus?: string | null;
}) {
  const { nodes, edges } = useMemo(() => {
    const findActor = (name: string) => actors.find((a) => getActorName(a) === name);
    const terminal = isTerminalRunStatus(runStatus);
    const eventsByActor = groupEventsByActor(executionEvents);

    const sup = findActor("supervisor_agent");
    const supStatus = getStatus(sup, terminal);
    const supActive = "supervisor_agent" === activeActorName;

    const specialists = [
      { name: "faq_agent", altName: "faq_specialist", desc: "FAQ e contexto geral", y: 0 },
      { name: "stock_agent", altName: "stock_specialist", desc: "estoque e disponibilidade", y: 130 },
      { name: "image_intake_agent", altName: "image_specialist", desc: "imagem ou documento", y: 260 },
    ];

    const respActor = findActor("response_streamer");
    const respStatus = getStatus(respActor, terminal);
    const respActive = "response_streamer" === activeActorName;

    const nodes: Node<AgentNodeData>[] = [
      makeNode(
        "supervisor_agent", "Agente Supervisor", "orquestra e roteia",
        supStatus, supActive, 0, 130, "info", getNodeId(sup), undefined,
        eventsByActor.get("supervisor_agent"),
      ),
      ...specialists.map((s) => {
        const actor = findActor(s.name) ?? findActor(s.altName);
        const resolvedName = actor ? (getActorName(actor) ?? s.name) : s.name;
        const status = actor ? getStatus(actor, terminal) : terminal ? "not_invoked" : "pending";
        const isActive = s.name === activeActorName || s.altName === activeActorName;
        const agentEvents = eventsByActor.get(s.name) ?? eventsByActor.get(s.altName) ?? [];
        return makeNode(
          s.name,
          formatAgentName(resolvedName),
          s.desc,
          status,
          isActive,
          280,
          s.y,
          actor ? undefined : "muted",
          getNodeId(actor),
          undefined,
          agentEvents,
        );
      }),
      makeNode(
        "response_streamer", "Streamer de Resposta", "sintetiza a resposta",
        respStatus, respActive, 560, 130, undefined, getNodeId(respActor), undefined,
        eventsByActor.get("response_streamer"),
      ),
    ];

    const centralizedAltNames = new Map<string, string[]>();
    centralizedAltNames.set("supervisor_agent", []);
    centralizedAltNames.set("response_streamer", []);
    for (const s of specialists) {
      centralizedAltNames.set(s.name, [s.altName]);
    }

    const edges: Edge[] = [
      ...specialists.map((s) =>
        makeEdge("supervisor_agent", s.name, edgeStateFromEvents(executionEvents, "supervisor_agent", s.name, terminal, centralizedAltNames)),
      ),
      ...specialists.map((s) =>
        makeEdge(s.name, "response_streamer", edgeStateFromEvents(executionEvents, s.name, "response_streamer", terminal, centralizedAltNames)),
      ),
    ];

    return { nodes, edges };
  }, [activeActorName, actors, executionEvents, runStatus]);

  return <FlowWrapper nodes={nodes} edges={edges} testId="runtime-visual-centralized" height={360} />;
}

// ---------------------------------------------------------------------------
// WorkflowFlow
// ---------------------------------------------------------------------------

export function WorkflowFlow({
  activeActorName,
  stages,
  executionEvents,
  runStatus,
}: {
  activeActorName: string;
  stages: unknown[];
  executionEvents: RunExecutionEvent[];
  runStatus?: string | null;
}) {
  const { nodes, edges } = useMemo(() => {
    const terminal = isTerminalRunStatus(runStatus);
    const eventsByActor = groupEventsByActor(executionEvents);

    const sequence = [
      { stage: "classify", actor: "router_agent", altActors: ["router_agent"], desc: "Classificar intenção" },
      { stage: "gather_evidence", actor: "workflow_evidence_agent", altActors: ["faq_agent", "stock_agent", "image_intake_agent"], desc: "Coletar Evidências" },
      { stage: "multimodal_analysis", actor: "workflow_multimodal_agent", altActors: ["image_intake_agent", "multi_modal", "multimodal_agent"], desc: "Análise Multimodal" },
      { stage: "review_gate", actor: "workflow_review_agent", altActors: ["review_agent"], desc: "Portão de Revisão" },
      { stage: "synthesize", actor: "workflow_synthesis_agent", altActors: ["synthesis_agent"], desc: "Sintetizar saída" },
    ];

    const altNameMap = new Map<string, string[]>();
    for (const step of sequence) {
      altNameMap.set(step.actor, step.altActors);
    }

    const nodes: Node<AgentNodeData>[] = sequence.map((step, i) => {
      const matching = stages.filter((s) => getStage(s) === step.stage).at(-1);
      const actorName = getActorName(matching) ?? step.actor;
      const status = matching
        ? getStatus(matching, terminal)
        : terminal && step.stage === "multimodal_analysis"
          ? "not_applicable"
          : terminal
            ? "not_invoked"
            : "pending";
      const active = actorName === activeActorName || step.altActors.includes(activeActorName);
      const tone: BadgeProps["variant"] | undefined = matching ? undefined : "muted";
      const agentEvents = eventsByActor.get(step.actor) ?? step.altActors.flatMap((alt) => eventsByActor.get(alt) ?? []);
      return makeNode(step.actor, formatAgentName(actorName), step.desc, status, active, i * 200, 0, tone, getNodeId(matching), undefined, agentEvents);
    });

    const edges: Edge[] = nodes.slice(0, -1).map((n, i) => {
      const next = nodes[i + 1];
      return makeEdge(n.id, next.id, edgeStateFromEvents(executionEvents, n.id, next.id, terminal, altNameMap));
    });

    return { nodes, edges };
  }, [activeActorName, executionEvents, runStatus, stages]);

  return <FlowWrapper nodes={nodes} edges={edges} testId="runtime-visual-workflow" height={300} />;
}

// ---------------------------------------------------------------------------
// SwarmFlow — peer-to-peer mesh topology
// ---------------------------------------------------------------------------

export function SwarmFlow({
  activeActorName,
  actors,
  executionEvents,
  handoffs,
  runStatus,
}: {
  activeActorName: string;
  actors: unknown[];
  executionEvents: RunExecutionEvent[];
  handoffs: unknown[];
  runStatus?: string | null;
}) {
  const { nodes, edges } = useMemo(() => {
    const findActor = (name: string) => actors.find((a) => getActorName(a) === name);
    const terminal = isTerminalRunStatus(runStatus);
    const eventsByActor = groupEventsByActor(executionEvents);

    const peerDefs = [
      { id: "swarm_coordinator", altName: "swarm_coordinator", desc: "par inicial", x: 80, y: 0 },
      { id: "faq_specialist", altName: "faq_agent", desc: "FAQ", x: 320, y: 0 },
      { id: "stock_specialist", altName: "stock_agent", desc: "estoque", x: 0, y: 180 },
      { id: "image_specialist", altName: "image_intake_agent", desc: "imagem", x: 400, y: 180 },
      { id: "swarm_synthesizer", altName: "swarm_synthesizer", desc: "síntese", x: 200, y: 300 },
    ];

    const nodes: Node<AgentNodeData>[] = peerDefs.map((peer) => {
      const actor = findActor(peer.id) ?? findActor(peer.altName);
      const resolvedName = actor ? (getActorName(actor) ?? peer.id) : peer.id;
      const status = actor ? getStatus(actor, terminal) : terminal ? "not_invoked" : "pending";
      const isActive = peer.id === activeActorName || peer.altName === activeActorName;
      const agentEvents = eventsByActor.get(peer.id) ?? eventsByActor.get(peer.altName) ?? [];
      return makeNode(
        peer.id,
        formatAgentName(resolvedName),
        peer.desc,
        status,
        isActive,
        peer.x,
        peer.y,
        actor ? undefined : "muted",
        getNodeId(actor),
        undefined,
        agentEvents,
      );
    });

    const meshEdges: Edge[] = [];

    const observedHandoffs = new Set<string>();
    for (const h of handoffs) {
      const key = getHandoffPairKey(h);
      if (key) observedHandoffs.add(key);
    }
    for (const e of executionEvents) {
      if (e.eventFamily === "handoff") {
        const p = e.payload as Record<string, unknown>;
        const from = (p.from ?? e.actorName) as string | undefined;
        const to = (p.to ?? p.targetActor) as string | undefined;
        if (from && to) observedHandoffs.add(`${from}->${to}`);
      }
    }

    const peerIds = new Set(peerDefs.map((p) => p.id));
    const altToId = new Map(peerDefs.map((p) => [p.altName, p.id]));
    const swarmAltNames = new Map<string, string[]>();
    for (const p of peerDefs) {
      swarmAltNames.set(p.id, p.altName !== p.id ? [p.altName] : []);
    }
    const resolveId = (name: string) => peerIds.has(name) ? name : (altToId.get(name) ?? name);

    if (observedHandoffs.size > 0) {
      for (const pair of observedHandoffs) {
        const [rawFrom, rawTo] = pair.split("->");
        const from = resolveId(rawFrom);
        const to = resolveId(rawTo);
        if (from && to && peerIds.has(from) && peerIds.has(to) && from !== to) {
          const state = edgeStateFromEvents(executionEvents, from, to, terminal, swarmAltNames);
          meshEdges.push(makeEdge(from, to, state === "idle" ? "settled" : state));
        }
      }
    } else {
      meshEdges.push(makeEdge("swarm_coordinator", "faq_specialist", "idle"));
      meshEdges.push(makeEdge("swarm_coordinator", "stock_specialist", "idle"));
      meshEdges.push(makeEdge("swarm_coordinator", "image_specialist", "idle"));
      meshEdges.push(makeEdge("faq_specialist", "swarm_synthesizer", "idle"));
      meshEdges.push(makeEdge("stock_specialist", "swarm_synthesizer", "idle"));
      meshEdges.push(makeEdge("image_specialist", "swarm_synthesizer", "idle"));
      meshEdges.push(makeEdge("faq_specialist", "stock_specialist", "idle"));
      meshEdges.push(makeEdge("stock_specialist", "image_specialist", "idle"));
    }

    return { nodes, edges: meshEdges };
  }, [activeActorName, actors, executionEvents, handoffs, runStatus]);

  return <FlowWrapper nodes={nodes} edges={edges} testId="runtime-visual-swarm" height={400} />;
}

function isTerminalRunStatus(status: string | null | undefined): boolean {
  return Boolean(
    status && ["completed", "failed", "cancelled", "human_review_required"].includes(status),
  );
}

function formatNodeStatusLabel(status: string): string {
  if (status === "completed") return "concluído";
  if (status === "running") return "em andamento";
  if (status === "failed") return "falhou";
  if (status === "pending") return "pendente";
  if (status === "skipped") return "ignorado";
  if (status === "not_invoked") return "não acionado";
  if (status === "not_applicable") return "não aplicável";
  if (status === "human_review_required") return "revisão humana";
  return status;
}
