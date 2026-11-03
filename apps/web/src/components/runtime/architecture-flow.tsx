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
  useNodesInitialized,
  useReactFlow,
  useStore,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useReducedMotion } from "motion/react";
import { memo, useEffect, useId, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { observedAgentGraph } from "@/components/runtime/observed-agent-graph";
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
    <div className="min-h-0 overflow-y-auto overscroll-contain">
      {events.map((event) => {
        const isExpanded = expandedId === event.id;
        const payload = event.payload as Record<string, unknown> | undefined;

        return (
          <div key={event.id} className="border-b border-border/50 last:border-0">
            <button
              type="button"
              aria-expanded={isExpanded}
              className="flex w-full items-center gap-2 px-2.5 py-2 text-left text-xs transition-colors hover:bg-muted/50 focus-visible:bg-muted focus-visible:outline-none"
              onClick={(e) => {
                e.stopPropagation();
                setExpandedId(isExpanded ? null : event.id);
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
                {event.durationMs == null ? "" : `${event.durationMs} ms`}
              </span>
              <span aria-hidden="true" className={`text-muted-foreground motion-safe:transition-transform ${isExpanded ? "rotate-90" : ""}`}>
                ›
              </span>
            </button>
            {isExpanded ? (
              <div className="space-y-2 border-t border-dashed bg-muted/20 px-3 py-2 text-[11px]">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-muted-foreground">
                  <Badge variant={statusBadgeVariant(event.status)}>{formatNodeStatusLabel(event.status)}</Badge>
                  <span title={event.createdAt}>Evento #{event.sequenceNo}</span>
                  {event.source ? <span>{event.source}</span> : null}
                </div>
                {event.eventFamily === "tool" ? (
                  <ToolCallDetail payload={payload} />
                ) : (
                  <ResponseDetail payload={payload} />
                )}
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
    : status === "running" || status === "human_review_required" ? "bg-amber-500"
    : family === "tool" ? "bg-blue-500"
    : family === "handoff" ? "bg-purple-500"
    : family === "response" ? "bg-emerald-500"
    : family === "node" ? "bg-sky-400"
    : "bg-muted-foreground/50";

  return <span className={`h-2 w-2 shrink-0 rounded-full ${color}`} />;
}

function ToolCallDetail({ payload }: { payload: Record<string, unknown> | undefined }) {
  if (!payload || !Object.keys(payload).length) return <p className="text-muted-foreground">Sem dados adicionais.</p>;

  const { input, result, ...metadata } = payload;

  return (
    <div className="space-y-1.5">
      {input != null ? (
        <div>
          <p className="font-medium text-foreground">Entrada</p>
          <pre className="mt-0.5 max-h-20 overflow-auto rounded bg-background p-1.5 text-[10px] text-muted-foreground">
            {JSON.stringify(input, null, 2)}
          </pre>
        </div>
      ) : null}
      {result != null ? (
        <div>
          <p className="font-medium text-foreground">Resultado</p>
          <pre className="mt-0.5 max-h-20 overflow-auto rounded bg-background p-1.5 text-[10px] text-muted-foreground">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      ) : null}
      <PayloadMetadata payload={metadata} />
    </div>
  );
}

function PayloadMetadata({ payload }: { payload: Record<string, unknown> }) {
  if (!Object.keys(payload).length) return null;
  return (
    <details>
      <summary className="cursor-pointer font-medium text-muted-foreground focus-visible:outline-primary">Metadados</summary>
      <pre className="mt-1 max-h-32 overflow-auto rounded bg-background p-1.5 text-[10px] text-muted-foreground">
        {JSON.stringify(payload, null, 2)}
      </pre>
    </details>
  );
}

function ResponseDetail({ payload }: { payload: Record<string, unknown> | undefined }) {
  if (!payload || !Object.keys(payload).length) return <p className="text-muted-foreground">Sem dados adicionais.</p>;
  const { contentText, outputText, text, inputText, ...metadata } = payload;
  const content = contentText ?? outputText ?? text ?? inputText;
  return (
    <div className="space-y-1">
      {typeof content === "string" && content ? (
        <p className="max-h-24 overflow-auto whitespace-pre-wrap break-words leading-relaxed text-foreground">
          {content}
        </p>
      ) : null}
      <PayloadMetadata payload={typeof content === "string" ? metadata : payload} />
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
  width: number;
  maxHeight: number;
}

function popoverPosition(card: HTMLElement): PopoverPosition {
  const rect = card.getBoundingClientRect();
  const width = Math.min(320, window.innerWidth - 16);
  const spaceBelow = window.innerHeight - rect.bottom - 14;
  const spaceAbove = rect.top - 14;
  const below = spaceBelow >= 280 || spaceBelow >= spaceAbove;
  const top = below ? rect.bottom + 6 : rect.top - 6;
  return {
    top,
    below,
    width,
    left: Math.max(8, Math.min(rect.left + (rect.width - width) / 2, window.innerWidth - width - 8)),
    maxHeight: Math.max(100, Math.min(320, below ? spaceBelow : spaceAbove)),
  };
}

const AgentNode = memo(function AgentNode({ data }: NodeProps<Node<AgentNodeData>>) {
  const { actorName, description, status, statusLabel, active, tone, nodeId, events } = data;
  const [popoverPos, setPopoverPos] = useState<PopoverPosition | null>(null);
  const popoverId = useId();
  const cardRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const dismissTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pinned = useRef(false);
  const agentEvents = (events ?? []) as RunExecutionEvent[];
  const eventCount = agentEvents.length;
  const toolCount = new Set(
    agentEvents
      .filter((event) => event.eventFamily === "tool" && event.eventName === "started")
      .map((event) => event.payload?.toolCallId ?? event.id),
  ).size;
  const responseCount = agentEvents.filter((e) => e.eventFamily === "response").length;

  const cancelDismiss = () => {
    if (dismissTimer.current) {
      clearTimeout(dismissTimer.current);
      dismissTimer.current = null;
    }
  };

  const closePopover = (restoreFocus = false) => {
    cancelDismiss();
    pinned.current = false;
    setPopoverPos(null);
    if (restoreFocus) triggerRef.current?.focus();
  };

  const popoverOpen = popoverPos !== null && eventCount > 0;
  const viewport = useStore((state) => popoverOpen ? state.transform : null);
  useEffect(() => {
    if (viewport && cardRef.current) setPopoverPos(popoverPosition(cardRef.current));
  }, [viewport]);

  useEffect(() => {
    if (!popoverOpen) return;

    const reposition = (event: Event) => {
      if (event.target instanceof globalThis.Node && popoverRef.current?.contains(event.target)) return;
      if (cardRef.current) setPopoverPos(popoverPosition(cardRef.current));
    };
    const dismissOutside = (event: PointerEvent) => {
      if (
        event.target instanceof globalThis.Node
        && !cardRef.current?.contains(event.target)
        && !popoverRef.current?.contains(event.target)
      ) {
        closePopover();
      }
    };
    const dismissOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        const focusInside = popoverRef.current?.contains(document.activeElement);
        closePopover(Boolean(focusInside));
      }
    };
    window.addEventListener("resize", reposition);
    window.addEventListener("scroll", reposition, true);
    document.addEventListener("pointerdown", dismissOutside);
    document.addEventListener("keydown", dismissOnEscape);
    return () => {
      cancelDismiss();
      window.removeEventListener("resize", reposition);
      window.removeEventListener("scroll", reposition, true);
      document.removeEventListener("pointerdown", dismissOutside);
      document.removeEventListener("keydown", dismissOnEscape);
    };
  }, [popoverOpen]);

  const showPopover = () => {
    cancelDismiss();
    if (cardRef.current && eventCount > 0) {
      setPopoverPos(popoverPosition(cardRef.current));
    }
  };

  const scheduleDismiss = () => {
    cancelDismiss();
    if (pinned.current) return;
    dismissTimer.current = setTimeout(() => {
      if (!popoverRef.current?.contains(document.activeElement)) closePopover();
    }, 160);
  };

  const restingStyle = status === "completed"
    ? "border-emerald-200 bg-emerald-50/80"
    : status === "failed"
      ? "border-destructive/45 bg-destructive/5"
      : status === "human_review_required"
        ? "border-amber-300 bg-amber-50"
      : status === "skipped" || status === "not_invoked" || status === "not_applicable" || tone === "muted"
        ? "border-dashed border-border/70 bg-muted/20"
        : "border-border bg-background";

  return (
    <div className="relative">
      <div
        ref={cardRef}
        className={`w-44 rounded-2xl border px-3 py-2.5 shadow-sm motion-safe:transition-colors ${
          active ? "border-amber-400 bg-amber-50 ring-2 ring-amber-500/20" : restingStyle
        }`}
        data-status={status}
        onPointerEnter={(event) => { if (event.pointerType === "mouse") showPopover(); }}
        onPointerLeave={(event) => { if (event.pointerType === "mouse") scheduleDismiss(); }}
      >
        <Handle type="target" position={Position.Left} className="!bg-transparent !border-0 !w-0 !h-0" />
        <Handle type="source" position={Position.Right} className="!bg-transparent !border-0 !w-0 !h-0" />
        <Handle id="reverse-in" type="target" position={Position.Right} className="!bg-transparent !border-0 !w-0 !h-0" />
        <Handle id="reverse-out" type="source" position={Position.Left} className="!bg-transparent !border-0 !w-0 !h-0" />
        <div className="flex items-center gap-2">
          <span
            className={`h-2.5 w-2.5 shrink-0 rounded-full ${
              active
                ? "bg-amber-500 motion-safe:animate-pulse"
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
          <p className="truncate text-sm font-semibold" title={actorName}>{actorName}</p>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">{description}</p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Badge variant={status === "pending" && tone ? tone : statusBadgeVariant(status)}>
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
        {eventCount > 0 ? (
          <button
            ref={triggerRef}
            type="button"
            aria-label={`Eventos de ${actorName}`}
            aria-expanded={popoverOpen}
            aria-controls={popoverOpen ? popoverId : undefined}
            className="nodrag nopan mt-1.5 rounded text-[11px] font-medium text-primary underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
            onClick={(event) => {
              event.stopPropagation();
              if (pinned.current) {
                closePopover();
                return;
              }
              pinned.current = true;
              showPopover();
              if (event.detail === 0) {
                requestAnimationFrame(() => popoverRef.current?.querySelector("button")?.focus());
              }
            }}
          >
            Ver eventos
          </button>
        ) : null}
      </div>

      {popoverOpen && popoverPos
        ? createPortal(
            <div
              ref={popoverRef}
              id={popoverId}
              role="region"
              aria-label={`Eventos de ${actorName}`}
              className="z-[60] flex flex-col rounded-lg border bg-card shadow-xl"
              style={{
                position: "fixed",
                top: popoverPos.below ? popoverPos.top : undefined,
                bottom: popoverPos.below ? undefined : window.innerHeight - popoverPos.top,
                left: popoverPos.left,
                width: popoverPos.width,
                maxHeight: popoverPos.maxHeight,
              }}
              onPointerEnter={cancelDismiss}
              onPointerLeave={scheduleDismiss}
            >
              <div className="flex items-center justify-between gap-3 border-b px-3 py-2">
                <div className="min-w-0">
                  <p className="truncate text-xs font-semibold" title={actorName}>{actorName}</p>
                  <span className="block truncate text-[11px] text-muted-foreground" title={nodeId ?? undefined}>
                    {eventCount} {eventCount === 1 ? "evento" : "eventos"}
                    {nodeId ? ` · ${nodeId}` : ""}
                  </span>
                </div>
                <button
                  type="button"
                  aria-label="Fechar eventos"
                  className="rounded px-2 py-1 text-sm text-muted-foreground hover:bg-muted focus-visible:outline-primary"
                  onClick={() => closePopover(true)}
                >
                  ×
                </button>
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
  const { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data, label } = props;
  const state = (data?.state as EdgeState) ?? "idle";
  const markerPrefix = data?.markerPrefix;
  const reduceMotion = useReducedMotion();

  const [bezierPath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });
  const bend = data?.bypass ? 90 : data?.return ? 54 : 0;
  const offset = (targetX - sourceX) / 3;
  const edgePath = bend
    ? `M ${sourceX},${sourceY} C ${sourceX + offset},${sourceY + bend} ${targetX - offset},${targetY + bend} ${targetX},${targetY}`
    : bezierPath;

  const color = EDGE_COLORS[state];
  const strokeWidth = state === "active" ? 2.5 : state === "recent" ? 2 : state === "settled" ? 1.6 : 1;
  const animated = !reduceMotion && state === "active";

  return (
    <g data-edge-state={state}>
      {label ? <title>{label}</title> : null}
      <BaseEdge
        path={edgePath}
        style={{
          stroke: color,
          strokeWidth,
          opacity: state === "idle" ? 0.6 : 0.9,
        }}
        markerEnd={`url(#${markerPrefix}-marker-${state})`}
      />
      {animated && (
        <path
          d={edgePath}
          fill="none"
          stroke="#60a5fa"
          strokeWidth={4}
          strokeLinecap="round"
          pathLength={100}
          strokeDasharray="9 91"
          pointerEvents="none"
          aria-hidden="true"
          data-edge-motion
        >
          <animate attributeName="stroke-dashoffset" from="100" to="0" dur="1.2s" repeatCount="indefinite" />
        </path>
      )}
    </g>
  );
}

// ---------------------------------------------------------------------------
// SVG marker definitions for edge arrows
// ---------------------------------------------------------------------------

function EdgeMarkerDefs({ prefix }: { prefix: string }) {
  return (
    <svg className="absolute h-0 w-0">
      <defs>
        {(["active", "recent", "settled", "idle"] as EdgeState[]).map((state) => (
          <marker
            key={state}
            id={`${prefix}-marker-${state}`}
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
const flowFitOptions = { padding: 0.16, maxZoom: 1 };

function FitGraph({ topology }: { topology: string }) {
  const { fitView } = useReactFlow();
  const ready = useNodesInitialized();
  const width = useStore((state) => state.width);
  const height = useStore((state) => state.height);
  useEffect(() => {
    if (ready) void fitView(flowFitOptions);
  }, [fitView, height, ready, topology, width]);
  return null;
}

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
  const markerPrefix = useId();
  const markedEdges = useMemo(() => edges.map((edge) => ({
    ...edge,
    data: { ...edge.data, markerPrefix },
  })), [edges, markerPrefix]);
  const topology = nodes.map(({ id, position }) => `${id}:${position.x},${position.y}`).join("|");
  return (
    <div data-testid={testId}>
      <p className="px-2 pt-1 text-xs text-muted-foreground sm:hidden">
        Deslize horizontalmente para ver todas as etapas.
      </p>
      <div
        aria-label="Grafo da execução"
        role="region"
        tabIndex={0}
        className="overflow-x-auto rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary"
      >
        <div style={{ height }} className="relative min-w-[620px]">
          <EdgeMarkerDefs prefix={markerPrefix} />
          <ReactFlow
            nodes={nodes}
            edges={markedEdges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
            fitViewOptions={flowFitOptions}
            proOptions={{ hideAttribution: true }}
            nodesDraggable={false}
            nodesConnectable={false}
            nodesFocusable={false}
            edgesFocusable={false}
            elementsSelectable={false}
            panOnDrag={false}
            zoomOnScroll={false}
            zoomOnPinch={false}
            zoomOnDoubleClick={false}
            preventScrolling={false}
          >
            <FitGraph topology={topology} />
          </ReactFlow>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const AGENT_NAME_MAP: Record<string, string> = {
  supervisor: "Supervisor",
  faq: "FAQ",
  stock: "Estoque",
  attachments: "Anexos",
  router: "Roteador",
  coordinator: "Iniciador",
  synthesizer: "Sintetizador",
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
  swarm_coordinator: "Iniciador",
  coordinator_agent: "Iniciador",
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
  if (status === "running" || status === "human_review_required") return "warning";
  if (status === "failed") return "destructive";
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

function lifecycleStatus(events: RunExecutionEvent[]): string | undefined {
  const latest = events.at(-1);
  if (latest?.status === "running") return "running";
  return events.filter((event) => event.eventFamily === "node" || event.eventFamily === "actor").at(-1)?.status;
}

function graphNodeStatus(
  status: string,
  events: RunExecutionEvent[],
  active: boolean,
  terminal: boolean,
): string {
  const latest = lifecycleStatus(events) ?? (active && status === "pending" ? "running" : status);
  if (terminal && latest === "running") return "interrupted";
  return terminal && latest === "pending" ? "not_invoked" : latest;
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
    // ReactFlow disables pointer-events on the wrapper when selectable/draggable/click handlers
    // are all off. We need hover for the agent popover, so re-enable pointer events here.
    style: { pointerEvents: "all" },
    data: { actorName, description, status, statusLabel, active: status === "running" && active, tone, nodeId, events: events ?? [] },
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

  const endpointStatus = (names: Set<string>) => {
    const related = events.filter((event) => event.actorName && names.has(event.actorName));
    return lifecycleStatus(related) ?? related.filter((event) =>
      event.eventFamily === "tool" || event.eventFamily === "response").at(-1)?.status;
  };
  const sourceStatus = endpointStatus(sourceNames);
  const targetStatus = endpointStatus(targetNames);

  // Explicit handoff between this exact pair always wins.
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i];
    if (e.eventFamily !== "handoff") continue;
    const actor = e.actorName;
    const p = (e.payload ?? {}) as Record<string, unknown>;
    const from = (p.from as string | undefined) ?? actor ?? undefined;
    const to = (p.to ?? p.targetActor) as string | undefined;
    if (from && to && sourceNames.has(from) && targetNames.has(to)) {
      return !terminal && (targetStatus === "running" || (targetStatus == null && e.status === "running"))
        ? "active" : "settled";
    }
  }

  if (sourceStatus !== "completed" && sourceStatus !== "running") return "idle";
  if (targetStatus === "running" && !terminal) return "active";
  return targetStatus === "completed" || targetStatus === "failed" ? "settled" : "idle";
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
    const supEvents = eventsByActor.get("supervisor_agent") ?? [];
    const supStatus = graphNodeStatus(getStatus(sup, terminal), supEvents, "supervisor_agent" === activeActorName, terminal);

    const specialists = [
      { name: "faq_agent", altName: "faq_specialist", desc: "FAQ e contexto geral", y: 0 },
      { name: "stock_agent", altName: "stock_specialist", desc: "estoque e disponibilidade", y: 130 },
      { name: "image_intake_agent", altName: "image_specialist", desc: "imagem ou documento", y: 260 },
    ];

    const respActor = findActor("response_streamer");
    const respEvents = eventsByActor.get("response_streamer") ?? [];
    const respStatus = graphNodeStatus(getStatus(respActor, terminal), respEvents, "response_streamer" === activeActorName, terminal);

    const nodes: Node<AgentNodeData>[] = [
      makeNode(
        "supervisor_agent", "Agente Supervisor", "orquestra e roteia",
        supStatus, !terminal, 0, 130, "info", getNodeId(sup), undefined, supEvents,
      ),
      ...specialists.map((s) => {
        const actor = findActor(s.name) ?? findActor(s.altName);
        const resolvedName = actor ? (getActorName(actor) ?? s.name) : s.name;
        const isActive = s.name === activeActorName || s.altName === activeActorName;
        const agentEvents = eventsByActor.get(s.name) ?? eventsByActor.get(s.altName) ?? [];
        const status = graphNodeStatus(actor ? getStatus(actor, terminal) : terminal ? "not_invoked" : "pending", agentEvents, isActive, terminal);
        return makeNode(
          s.name,
          formatAgentName(resolvedName),
          s.desc,
          status,
          !terminal,
          280,
          s.y,
          actor ? undefined : "muted",
          getNodeId(actor),
          undefined,
          agentEvents,
        );
      }),
      makeNode(
        "response_streamer", "Síntese da resposta", "redige a saída final",
        respStatus, !terminal, 560, 130, undefined, getNodeId(respActor), undefined, respEvents,
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

  if (usesObservedAgentTrace(executionEvents)) {
    return <ObservedAgentFlow executionEvents={executionEvents} runStatus={runStatus} testId="runtime-visual-centralized" />;
  }
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
      const projectedStatus = matching
        ? getStatus(matching, terminal)
        : terminal && step.stage === "multimodal_analysis"
          ? "not_applicable"
          : terminal
            ? "not_invoked"
            : "pending";
      const active = actorName === activeActorName || step.altActors.includes(activeActorName);
      const tone: BadgeProps["variant"] | undefined = matching ? undefined : "muted";
      const agentEvents = [...new Set([step.actor, ...step.altActors])]
        .flatMap((actor) => eventsByActor.get(actor) ?? [])
        .filter((event) => {
          const eventStage = event.payload.stage ?? event.payload.phase;
          return eventStage === step.stage || !sequence.some(({ stage }) => stage === eventStage);
        })
        .sort((a, b) => a.sequenceNo - b.sequenceNo);
      const status = graphNodeStatus(projectedStatus, agentEvents, active, terminal);
      return makeNode(step.actor, formatAgentName(actorName), step.desc, status, !terminal, i * 200, 0, tone, getNodeId(matching), undefined, agentEvents);
    });

    const edges: Edge[] = nodes.slice(0, -1).map((n, i) => {
      const next = nodes[i + 1];
      return makeEdge(n.id, next.id, edgeStateFromEvents(executionEvents, n.id, next.id, terminal, altNameMap));
    });
    // Optional stages stay visible. When the execution bypasses them, draw the
    // observed path between the last executed stage and the next executed one.
    const executed = nodes.filter(({ data }) =>
      ["running", "completed", "failed", "human_review_required", "interrupted"].includes(data.status));
    for (let i = 1; i < executed.length; i++) {
      const previous = executed[i - 1];
      const current = executed[i];
      if (current.position.x - previous.position.x > 200 && previous.data.status === "completed") {
        edges.push({
          ...makeEdge(previous.id, current.id, current.data.status === "running" ? "active" : "settled"),
          label: "Fluxo entre etapas executadas",
          data: { state: current.data.status === "running" ? "active" : "settled", bypass: true },
        });
      }
    }

    return { nodes, edges };
  }, [activeActorName, executionEvents, runStatus, stages]);

  if (usesObservedAgentTrace(executionEvents)) {
    return <ObservedAgentFlow executionEvents={executionEvents} runStatus={runStatus} testId="runtime-visual-workflow" />;
  }
  return <FlowWrapper nodes={nodes} edges={edges} testId="runtime-visual-workflow" height={210} />;
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

    const peerDefs: Array<{ id: string; altNames: string[]; desc: string; x: number; y: number }> = [
      { id: "swarm_coordinator", altNames: ["coordinator_agent"], desc: "abre a colaboração", x: 80, y: 0 },
      { id: "faq_specialist", altNames: ["faq_agent"], desc: "FAQ", x: 320, y: 0 },
      { id: "stock_specialist", altNames: ["stock_agent"], desc: "estoque", x: 0, y: 152 },
      { id: "image_specialist", altNames: ["image_intake_agent"], desc: "imagem", x: 400, y: 152 },
      { id: "swarm_synthesizer", altNames: [], desc: "síntese", x: 200, y: 282 },
    ];

    const nodes: Node<AgentNodeData>[] = peerDefs.map((peer) => {
      const actor = findActor(peer.id) ?? peer.altNames.map((alt) => findActor(alt)).find(Boolean);
      const resolvedName = actor ? (getActorName(actor) ?? peer.id) : peer.id;
      const isActive = peer.id === activeActorName || peer.altNames.includes(activeActorName);
      const agentEvents =
        eventsByActor.get(peer.id) ??
        peer.altNames.map((alt) => eventsByActor.get(alt)).find(Boolean) ??
        [];
      const status = graphNodeStatus(actor ? getStatus(actor, terminal) : terminal ? "not_invoked" : "pending", agentEvents, isActive, terminal);
      return makeNode(
        peer.id,
        formatAgentName(resolvedName),
        peer.desc,
        status,
        !terminal,
        peer.x,
        peer.y,
        actor ? undefined : "muted",
        getNodeId(actor),
        undefined,
        agentEvents,
      );
    });

    const peerIds = new Set(peerDefs.map((p) => p.id));
    const altToId = new Map<string, string>();
    for (const p of peerDefs) {
      for (const alt of p.altNames) altToId.set(alt, p.id);
    }
    const swarmAltNames = new Map<string, string[]>();
    for (const p of peerDefs) {
      swarmAltNames.set(p.id, p.altNames);
    }
    const resolveId = (name: string) => (peerIds.has(name) ? name : (altToId.get(name) ?? name));

    // Collect observed handoffs from architectureView and from execution events.
    // Live runs may emit handoffs without an explicit 'from' in the payload — in
    // that case we infer the source as the most recent actor that started/completed
    // work before the handoff event.
    const observedHandoffs = new Set<string>();
    const recordPair = (rawFrom: unknown, rawTo: unknown) => {
      if (typeof rawFrom !== "string" || typeof rawTo !== "string") return;
      const from = resolveId(rawFrom);
      const to = resolveId(rawTo);
      if (peerIds.has(from) && peerIds.has(to) && from !== to) {
        observedHandoffs.add(`${from}->${to}`);
      }
    };

    for (const h of handoffs) {
      if (!h || typeof h !== "object") continue;
      const payload = (h as Record<string, unknown>).payload;
      if (!payload || typeof payload !== "object") continue;
      const p = payload as Record<string, unknown>;
      recordPair(p.from, p.to ?? p.targetActor);
    }

    let lastActiveActor: string | null = null;
    for (const e of executionEvents) {
      if (e.eventFamily === "handoff") {
        const p = (e.payload ?? {}) as Record<string, unknown>;
        const inferredFrom = (p.from as string | undefined) ?? lastActiveActor ?? "swarm_coordinator";
        const inferredTo = (p.to ?? p.targetActor ?? e.actorName) as string | undefined;
        recordPair(inferredFrom, inferredTo);
        if (typeof inferredTo === "string") lastActiveActor = resolveId(inferredTo);
      } else if (e.actorName && (e.eventFamily === "node" || e.eventFamily === "tool" || e.eventFamily === "response")) {
        const id = resolveId(e.actorName);
        if (peerIds.has(id)) lastActiveActor = id;
      }
    }

    // Always render the canonical swarm topology so the structure is visible,
    // and elevate edges that match an observed handoff to "active/recent/settled".
    const canonicalEdges: Array<[string, string]> = [
      ["swarm_coordinator", "faq_specialist"],
      ["swarm_coordinator", "stock_specialist"],
      ["swarm_coordinator", "image_specialist"],
      ["faq_specialist", "swarm_synthesizer"],
      ["stock_specialist", "swarm_synthesizer"],
      ["image_specialist", "swarm_synthesizer"],
      ["swarm_coordinator", "swarm_synthesizer"],
    ];

    const edgeMap = new Map<string, Edge>();
    for (const [from, to] of canonicalEdges) {
      const pair = `${from}->${to}`;
      if (!observedHandoffs.has(pair)) {
        edgeMap.set(pair, makeEdge(from, to, "idle"));
        continue;
      }
      const state = edgeStateFromEvents(executionEvents, from, to, terminal, swarmAltNames);
      edgeMap.set(pair, makeEdge(from, to, state === "idle" ? "settled" : state));
    }

    // Add any observed peer-to-peer handoff that isn't part of the canonical layout
    // (e.g. faq_specialist -> stock_specialist in a chained delegation).
    for (const pair of observedHandoffs) {
      if (edgeMap.has(pair)) continue;
      const [from, to] = pair.split("->");
      if (!from || !to) continue;
      const state = edgeStateFromEvents(executionEvents, from, to, terminal, swarmAltNames);
      const finalState: EdgeState = state === "idle" ? "settled" : state;
      edgeMap.set(pair, makeEdge(from, to, finalState));
    }

    return { nodes, edges: Array.from(edgeMap.values()) };
  }, [activeActorName, actors, executionEvents, handoffs, runStatus]);

  if (usesObservedAgentTrace(executionEvents)) {
    return <ObservedAgentFlow executionEvents={executionEvents} runStatus={runStatus} testId="runtime-visual-swarm" />;
  }
  return <FlowWrapper nodes={nodes} edges={edges} testId="runtime-visual-swarm" />;
}

function usesObservedAgentTrace(events: RunExecutionEvent[]) {
  return events.length === 0 || events.some((event) => event.eventFamily === "agent" || event.source === "ai_service");
}

function ObservedAgentFlow({ executionEvents, runStatus, testId }: {
  executionEvents: RunExecutionEvent[];
  runStatus?: string | null;
  testId: string;
}) {
  const terminal = isTerminalRunStatus(runStatus);
  const { nodes, edges, height } = useMemo(() => {
    const graph = observedAgentGraph(executionEvents, terminal);
    const columns = new Map<string, number>();
    const rows = new Map<number, number>();
    const nodes = graph.agents.map((agent) => {
      const parent = graph.links.find((link) => link.kind === "call" && link.to === agent.role && columns.has(link.from));
      const column = parent ? (columns.get(parent.from) ?? 0) + 1 : 0;
      const row = rows.get(column) ?? 0;
      columns.set(agent.role, column);
      rows.set(column, row + 1);
      return makeNode(agent.role, formatAgentName(agent.role), parent ? "Especialista acionado" : "Agente acionado",
        agent.status, !terminal, column * 238, row * 128,
        undefined, agent.events.find((event) => event.nodeId)?.nodeId, undefined, agent.events);
    });
    const edges = graph.links.map((link) => {
      const isReturn = link.kind === "return";
      const reverse = (columns.get(link.from) ?? 0) > (columns.get(link.to) ?? 0);
      const state = link.status === "running" && !terminal ? "active" : isReturn ? "recent" : "settled";
      return {
        ...makeEdge(link.from, link.to, state),
        id: `${link.from}-${link.to}-${link.kind}`,
        sourceHandle: reverse ? "reverse-out" : undefined,
        targetHandle: reverse ? "reverse-in" : undefined,
        label: isReturn ? "Retorno registrado" : "Invocação registrada",
        data: { state, return: isReturn },
      };
    });
    return { nodes, edges, height: Math.max(220, Math.max(0, ...rows.values()) * 128 + 52) };
  }, [executionEvents, terminal]);
  return (
    <div data-testid="observed-agent-flow">
      {nodes.length ? (
        <>
          <p className="px-2 pt-1 text-xs text-muted-foreground">Agentes e comunicações registrados na execução. Abra os eventos para conferir entradas, fontes e retornos.</p>
          <FlowWrapper nodes={nodes} edges={edges} testId={testId} height={height} />
        </>
      ) : (
        <p data-testid={testId} className="px-3 py-6 text-center text-sm text-muted-foreground">
          {terminal ? "Nenhuma invocação de agente registrada." : "Aguardando registro de invocação de agente."}
        </p>
      )}
    </div>
  );
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
  if (status === "interrupted") return "interrompido";
  if (status === "waiting") return "aguardando";
  if (status === "cancelled") return "cancelado";
  if (status === "accepted") return "aceito";
  if (status === "processing") return "processando";
  if (status === "queued") return "na fila";
  if (status === "human_review_required") return "revisão humana";
  return status;
}
