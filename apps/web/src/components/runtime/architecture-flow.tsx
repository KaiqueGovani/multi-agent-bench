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
  getSmoothStepPath,
  type EdgeProps,
  useReactFlow,
  useStore,
  getViewportForBounds,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Maximize2, Minus, Plus } from "lucide-react";
import { useReducedMotion } from "motion/react";
import { memo, useEffect, useId, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { observedAgentGraph } from "@/components/runtime/observed-agent-graph";
import { routeSwarmEdge, type CardRect } from "@/components/runtime/edge-routing";
import type { RunExecutionEvent } from "@/lib/types";
import { ORCHESTRATOR_LABEL, formatDisplayTerminology } from "@/lib/ui-terminology";

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
  incomingEvidence?: RunExecutionEvent[];
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
                {formatDisplayTerminology(`${event.eventFamily}.${event.eventName}`)}
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

function SynthesisEvidence({ events }: { events: RunExecutionEvent[] }) {
  return (
    <section data-testid="workflow-evidence-inputs" aria-label="Evidências para a síntese" className="border-b p-2.5 text-[11px]">
      <h2 className="font-semibold">Evidências para a síntese</h2>
      <p className="mt-1 text-muted-foreground">Mensagens direcionadas ao Sintetizador nos eventos registrados.</p>
      {events.length ? events.map((event) => (
        <details key={event.id} className="mt-2 rounded border bg-muted/20 p-2">
          <summary className="cursor-pointer rounded font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary">
            {formatAgentName(event.actorName ?? "")}{` · evento #${event.sequenceNo}`}
          </summary>
          <div className="mt-2 space-y-1.5">
            <Badge variant={statusBadgeVariant(event.status)}>{formatNodeStatusLabel(event.status)}</Badge>
            <ResponseDetail payload={event.payload} />
          </div>
        </details>
      )) : <p className="mt-2 text-muted-foreground">Nenhuma evidência recebida registrada.</p>}
    </section>
  );
}

function synthesisEvidence(events: RunExecutionEvent[], recipients: string[]) {
  return events.filter((event) => event.eventFamily === "communication" && event.eventName === "message"
    && typeof event.payload?.to === "string" && recipients.includes(event.payload.to)
    && Boolean(event.actorName) && event.actorName !== event.payload.to)
    .sort((a, b) => a.sequenceNo - b.sequenceNo);
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
  const { actorName, description, status, statusLabel, active, tone, nodeId, events, incomingEvidence } = data;
  const [popoverPos, setPopoverPos] = useState<PopoverPosition | null>(null);
  const popoverId = useId();
  const cardRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const dismissTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pinned = useRef(false);
  const agentEvents = (events ?? []) as RunExecutionEvent[];
  const eventCount = agentEvents.length;
  const hasDetails = eventCount > 0 || Boolean(incomingEvidence?.length);
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

  const popoverOpen = popoverPos !== null && hasDetails;
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
    if (cardRef.current && hasDetails) {
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
        className={`w-44 ${data.uniformHeight ? "min-h-[132px]" : ""} rounded-2xl border px-3 py-2.5 shadow-sm motion-safe:transition-colors ${
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
        <Handle id="top-in" type="target" position={Position.Top} className="!bg-transparent !border-0 !w-0 !h-0" />
        <Handle id="top-out" type="source" position={Position.Top} className="!bg-transparent !border-0 !w-0 !h-0" />
        <Handle id="bottom-in" type="target" position={Position.Bottom} className="!bg-transparent !border-0 !w-0 !h-0" />
        <Handle id="bottom-out" type="source" position={Position.Bottom} className="!bg-transparent !border-0 !w-0 !h-0" />
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
        {hasDetails ? (
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
                  <span className="block truncate text-[11px] text-muted-foreground" title={nodeId ? formatDisplayTerminology(nodeId) : undefined}>
                    {eventCount} {eventCount === 1 ? "evento" : "eventos"}
                    {nodeId ? ` · ${formatDisplayTerminology(nodeId)}` : ""}
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
              <div className="min-h-0 overflow-y-auto overscroll-contain">
                {incomingEvidence !== undefined ? <SynthesisEvidence events={incomingEvidence} /> : null}
                <AgentEventTimeline events={agentEvents} />
              </div>
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
  const { sourcePosition, targetPosition, data, label } = props;
  const workflow = data?.workflow === true;
  const swarm = data?.swarm === true;
  const outward = (position: Position) => ({
    x: position === Position.Left ? -6 : position === Position.Right ? 6 : 0,
    y: position === Position.Top ? -6 : position === Position.Bottom ? 6 : 0,
  });
  const sourceOffset = workflow ? outward(sourcePosition) : { x: 0, y: 0 };
  const targetOffset = workflow ? outward(targetPosition) : { x: 0, y: 0 };
  const sourceX = props.sourceX + sourceOffset.x;
  const sourceY = props.sourceY + sourceOffset.y;
  const targetX = props.targetX + targetOffset.x;
  const targetY = props.targetY + targetOffset.y;
  const state = (data?.state as EdgeState) ?? "idle";
  const markerPrefix = data?.markerPrefix;
  const reduceMotion = useReducedMotion();
  const nodeLookup = useStore((store) => store.nodeLookup);
  const cardRect = (id: string): CardRect | undefined => {
    const node = nodeLookup.get(id);
    return node?.measured.width && node.measured.height
      ? { ...node.internals.positionAbsolute, width: node.measured.width, height: node.measured.height }
      : undefined;
  };
  const sourceCard = swarm ? cardRect(props.source) : undefined;
  const targetCard = swarm ? cardRect(props.target) : undefined;
  const swarmRoute = sourceCard && targetCard
    ? routeSwarmEdge(sourceCard, targetCard, [...nodeLookup.keys()].flatMap((id) => {
      const rect = cardRect(id);
      return rect ? [rect] : [];
    }))
    : undefined;

  const [bezierPath, bezierLabelX, bezierLabelY] = getBezierPath({
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

  const workflowBypass = workflow && data?.bypass === true;
  const routeOffset = typeof data?.lane === "number" ? 34 + data.lane * 18 : 34;
  const laneY = Math.min(sourceY, targetY) - routeOffset;
  const corner = 8;
  const [stepPath, stepLabelX, stepLabelY] = getSmoothStepPath({
    sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition,
    borderRadius: 8, offset: 12,
  });
  const bypassPath = `M ${sourceX},${sourceY} L ${sourceX},${laneY + corner} Q ${sourceX},${laneY} ${sourceX + Math.sign(targetX - sourceX) * corner},${laneY} L ${targetX - Math.sign(targetX - sourceX) * corner},${laneY} Q ${targetX},${laneY} ${targetX},${laneY + corner} L ${targetX},${targetY}`;
  const renderedPath = swarmRoute?.path ?? (workflow ? workflowBypass ? bypassPath : stepPath : edgePath);
  const labelX = workflow ? workflowBypass ? (sourceX + targetX) / 2 : stepLabelX : bezierLabelX;
  const labelY = workflow ? workflowBypass ? laneY : stepLabelY : bezierLabelY;

  const color = EDGE_COLORS[state];
  const strokeWidth = state === "active" ? 2.5 : state === "idle" ? 1.5 : 2;
  const animated = !reduceMotion && state === "active";
  const neutralSequence = data?.sequence && !workflow;
  const marker = `url(#${markerPrefix}-marker-${neutralSequence ? "sequence" : state})`;

  return (
    <g
      data-edge-state={state}
      data-edge-kind={data?.sequence ? "sequence" : "communication"}
      data-edge-direction={data?.bidirectional ? "both" : "forward"}
      data-edge-route={swarm ? swarmRoute?.detour ? "swarm-detour" : "swarm-direct" : workflow ? workflowBypass ? "workflow-bypass" : "workflow-forward" : undefined}
    >
      {label ? <title>{label}</title> : null}
      <BaseEdge
        path={renderedPath}
        style={{
          stroke: neutralSequence ? "#64748b" : color,
          strokeWidth,
          strokeLinecap: "round",
          strokeLinejoin: "round",
          opacity: state === "idle" ? 0.6 : 0.95,
          strokeDasharray: data?.sequence && !workflow ? "6 5" : undefined,
        }}
        markerStart={data?.bidirectional ? marker : undefined}
        markerEnd={marker}
        label={typeof data?.labelText === "string" ? data.labelText : undefined}
        labelX={labelX}
        labelY={labelY - 10}
        labelStyle={{ fill: "#475569", fontSize: 10, fontWeight: 500 }}
        labelBgStyle={{ fill: "#f8fafc", fillOpacity: 0.95 }}
        labelBgPadding={[5, 3]}
        labelBgBorderRadius={4}
      />
      {animated && (
        <path
          d={renderedPath}
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
        {(["active", "recent", "settled", "idle", "sequence"] as const).map((state) => (
          <marker
            key={state}
            id={`${prefix}-marker-${state}`}
            viewBox="0 0 10 10"
            refX="10"
            refY="5"
            markerWidth="10"
            markerHeight="10"
            markerUnits="userSpaceOnUse"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={state === "sequence" ? "#64748b" : EDGE_COLORS[state]} />
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
const flowFitOptions = { padding: 0.14, minZoom: 0.18, maxZoom: 1 };

function fittedBounds(bounds: CardRect, edges: Edge[]) {
  const top = Math.max(0, ...edges.filter((edge) => edge.data?.workflow && edge.data?.bypass)
    .map((edge) => 54 + (typeof edge.data?.lane === "number" ? edge.data.lane * 18 : 0)));
  const margin = edges.some((edge) => edge.data?.swarm) ? 24 : 0;
  return { x: bounds.x - margin, y: bounds.y - top - margin, width: bounds.width + margin * 2, height: bounds.height + top + margin * 2 };
}

function FlowControls() {
  const { getNodes, getNodesBounds, getEdges, setViewport, zoomIn, zoomOut } = useReactFlow();
  const width = useStore((state) => state.width);
  const height = useStore((state) => state.height);
  const fit = () => setViewport(getViewportForBounds(fittedBounds(getNodesBounds(getNodes()), getEdges()), width, height, 0.18, 1, 0.14));
  return (
    <div className="absolute right-2 top-2 z-10 flex items-center gap-0.5 rounded-md border bg-card/95 p-0.5 shadow-sm">
      <button aria-label="Diminuir fluxo" className="flex h-9 w-9 items-center justify-center rounded text-muted-foreground hover:bg-muted focus-visible:outline-primary sm:h-7 sm:w-7" onClick={() => void zoomOut()} type="button"><Minus className="h-3.5 w-3.5" /></button>
      <button aria-label="Ampliar fluxo" className="flex h-9 w-9 items-center justify-center rounded text-muted-foreground hover:bg-muted focus-visible:outline-primary sm:h-7 sm:w-7" onClick={() => void zoomIn()} type="button"><Plus className="h-3.5 w-3.5" /></button>
      <button aria-label="Ajustar fluxo" className="flex h-9 items-center gap-1 rounded px-1.5 text-[11px] text-muted-foreground hover:bg-muted focus-visible:outline-primary sm:h-7" onClick={() => void fit()} type="button"><Maximize2 className="h-3.5 w-3.5" /><span>Ajustar</span></button>
    </div>
  );
}

function FitGraph({ topology }: { topology: string }) {
  const { getNodes, getNodesBounds, getEdges, setViewport } = useReactFlow();
  const ready = useStore((state) => state.nodeLookup.size > 0 && [...state.nodeLookup.values()]
    .every((node) => Boolean(node.measured?.width && node.measured?.height)));
  const width = useStore((state) => state.width);
  const height = useStore((state) => state.height);
  useEffect(() => {
    let frame = 0;
    let settledFrame = 0;
    if (ready && width > 0 && height > 0) {
      // Read measured internal nodes: controlled input nodes intentionally do
      // not receive ReactFlow's dimension changes. Refit when the frame resizes.
      frame = requestAnimationFrame(() => {
        settledFrame = requestAnimationFrame(() => {
          const bounds = fittedBounds(getNodesBounds(getNodes()), getEdges());
          void setViewport(getViewportForBounds(bounds, width, height, 0.18, 1, 0.14));
        });
      });
    }
    return () => { cancelAnimationFrame(frame); cancelAnimationFrame(settledFrame); };
  }, [getNodes, getNodesBounds, getEdges, height, ready, setViewport, topology, width]);
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
  const canvasRef = useRef<HTMLDivElement>(null);
  const [canvasHeight, setCanvasHeight] = useState(height);
  useEffect(() => {
    const canvas = canvasRef.current;
    const panel = canvas?.closest<HTMLElement>('[data-testid="chat-flow-panel"]');
    const parent = panel?.parentElement;
    if (!canvas || !panel || !parent) {
      setCanvasHeight(height);
      return;
    }
    const resize = () => {
      const panelBox = panel.getBoundingClientRect();
      const available = Math.min(panel.clientHeight, parent.getBoundingClientRect().bottom - panelBox.top);
      const headingHeight = canvas.getBoundingClientRect().top - panelBox.top;
      setCanvasHeight(Math.min(height, Math.max(100, Math.floor(available - headingHeight - 8))));
    };
    const observer = new ResizeObserver(resize);
    observer.observe(panel);
    observer.observe(parent);
    resize();
    return () => observer.disconnect();
  }, [height]);
  const markedEdges = useMemo(() => edges.map((edge) => ({
    ...edge,
    data: { ...edge.data, markerPrefix },
  })), [edges, markerPrefix]);
  const topology = nodes.map(({ id, position }) => `${id}:${position.x},${position.y}`).join("|")
    + edges.map(({ id, data }) => `${id}:${data?.lane ?? 0}`).join("|");
  return (
    <div className="min-w-0 max-w-full" data-testid={testId}>
      <p className="px-2 pb-1 text-[11px] text-muted-foreground sm:hidden">Use + para ampliar e arraste para explorar.</p>
      <div
        aria-label="Grafo da execução"
        role="region"
        tabIndex={0}
        className="min-w-0 max-w-full overflow-hidden rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary"
      >
        <div ref={canvasRef} style={{ height: canvasHeight }} className="relative w-full min-w-0">
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
            panOnDrag
            minZoom={0.18}
            maxZoom={1.8}
            zoomOnScroll={false}
            zoomOnPinch
            zoomOnDoubleClick={false}
            preventScrolling={false}
          >
            <FitGraph topology={topology} />
            <FlowControls />
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
  supervisor: ORCHESTRATOR_LABEL,
  orchestrator: ORCHESTRATOR_LABEL,
  orquestrador: ORCHESTRATOR_LABEL,
  orchestrator_agent: ORCHESTRATOR_LABEL,
  faq: "FAQ",
  stock: "Estoque",
  attachments: "Anexos",
  router: "Roteador",
  coordinator: "Iniciador",
  synthesizer: "Sintetizador",
  supervisor_agent: ORCHESTRATOR_LABEL,
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

// Both runtime protocols expose these five peers. Positions are deliberately
// independent of which subset ran, so the collaboration map stays familiar.
const SWARM_ROSTER = [
  { id: "coordinator", label: "Coordenador", aliases: ["swarm_coordinator", "coordinator_agent"], description: "Coordena a colaboração", x: 264, y: 110 },
  { id: "faq", label: "FAQ", aliases: ["faq_specialist", "faq_agent"], description: "Informações de atendimento", x: 0, y: 0 },
  { id: "stock", label: "Estoque", aliases: ["stock_specialist", "stock_agent"], description: "Disponibilidade e preços", x: 528, y: 0 },
  { id: "attachments", label: "Anexos", aliases: ["image_specialist", "image_intake_agent", "attachments_specialist"], description: "Imagens e documentos", x: 0, y: 220 },
  { id: "synthesizer", label: "Sintetizador", aliases: ["swarm_synthesizer", "synthesis_agent"], description: "Compõe a resposta final", x: 528, y: 220 },
];

function swarmRole(role: string) {
  return SWARM_ROSTER.find((peer) => peer.id === role || peer.aliases.includes(role))?.id ?? role;
}

const TOOL_LABEL_MAP: Record<string, string> = {
  faq_lookup: "FAQ",
  stock_lookup: "Estoque",
  attachment_intake: "Anexo",
  handoff_to_peer: "Handoff",
};

function formatToolLabel(name: string): string {
  return TOOL_LABEL_MAP[name] ?? formatDisplayTerminology(name);
}

function formatAgentName(name: string): string {
  return AGENT_NAME_MAP[name.toLowerCase()] ?? formatDisplayTerminology(name);
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

function workflowConnections(nodes: Node<AgentNodeData>[]): Edge[] {
  // This view expresses stage order only. Recorded evidence belongs in the
  // recipient's details, not in extra routes that resemble skipped stages.
  return nodes.slice(1).map((target, index) => {
    const source = nodes[index];
    const state: EdgeState = source.data.status !== "completed" ? "idle"
      : target.data.status === "running" ? "active"
      : target.data.status === "completed" ? "settled" : "idle";
    return {
      ...makeEdge(source.id, target.id, state),
      id: `${source.id}-${target.id}-sequence`,
      label: "Ordem de execução",
      data: { state, workflow: true, sequence: true },
    };
  });
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
        "supervisor_agent", ORCHESTRATOR_LABEL, "orquestra e roteia",
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
    return <ObservedAgentFlow architecture="centralized" executionEvents={executionEvents} runStatus={runStatus} testId="runtime-visual-centralized" />;
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
      const node = makeNode(step.actor, formatAgentName(actorName), step.desc, status, !terminal, i * 200, 0, tone, getNodeId(matching), undefined, agentEvents);
      if (step.stage === "synthesize") node.data.incomingEvidence = synthesisEvidence(executionEvents, [step.actor, actorName, ...step.altActors, "synthesizer"]);
      return node;
    });

    return { nodes, edges: workflowConnections(nodes) };
  }, [activeActorName, executionEvents, runStatus, stages]);

  if (usesObservedAgentTrace(executionEvents)) {
    return <ObservedAgentFlow architecture="workflow" executionEvents={executionEvents} runStatus={runStatus} testId="runtime-visual-workflow" />;
  }
  return (
    <div className="min-w-0 max-w-full">
      <p className="px-2 py-1 text-xs leading-relaxed text-muted-foreground">Ordem das etapas. Etapas não acionadas permanecem identificadas nos cartões.</p>
      <div aria-label="Legenda das conexões" className="px-2 pb-2 text-[11px] text-muted-foreground">→ Ordem de execução</div>
      <FlowWrapper nodes={nodes} edges={edges} testId="runtime-visual-workflow" height={300} />
    </div>
  );
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

    const peerDefs = SWARM_ROSTER.map((peer) => ({
      id: peer.aliases[0], altNames: [peer.id, ...peer.aliases.slice(1)],
      desc: peer.description, label: peer.label, x: peer.x, y: peer.y,
    }));

    const nodes: Node<AgentNodeData>[] = peerDefs.map((peer) => {
      const actor = findActor(peer.id) ?? peer.altNames.map((alt) => findActor(alt)).find(Boolean);
      const isActive = peer.id === activeActorName || peer.altNames.includes(activeActorName);
      const agentEvents =
        eventsByActor.get(peer.id) ??
        peer.altNames.map((alt) => eventsByActor.get(alt)).find(Boolean) ??
        [];
      const invoked = agentEvents.length > 0 || Boolean(actor && getStatus(actor, terminal) !== "pending");
      const status = invoked ? graphNodeStatus(actor ? getStatus(actor, terminal) : "pending", agentEvents, isActive, terminal) : "not_invoked";
      const node = makeNode(
        peer.id,
        peer.label,
        peer.desc,
        status,
        !terminal,
        peer.x,
        peer.y,
        invoked ? undefined : "muted",
        getNodeId(actor),
        undefined,
        agentEvents,
      );
      node.data.uniformHeight = true;
      return node;
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

    const edgeMap = new Map<string, Edge>();
    const byId = new Map(nodes.map((node) => [node.id, node]));
    // Available peers stay visible, but a connecting line still requires a
    // recorded handoff. Neutral roster entries never imply an invocation.
    for (const pair of observedHandoffs) {
      if (edgeMap.has(pair)) continue;
      const [from, to] = pair.split("->");
      if (!from || !to) continue;
      const state = edgeStateFromEvents(executionEvents, from, to, terminal, swarmAltNames);
      const finalState: EdgeState = state === "idle" ? "settled" : state;
      edgeMap.set(pair, {
        ...makeEdge(from, to, finalState),
        ...connectionHandles(byId.get(from)!, byId.get(to)!),
        data: { state: finalState, swarm: true },
      });
    }

    return { nodes, edges: Array.from(edgeMap.values()) };
  }, [activeActorName, actors, executionEvents, handoffs, runStatus]);

  if (usesObservedAgentTrace(executionEvents)) {
    return <ObservedAgentFlow architecture="swarm" executionEvents={executionEvents} runStatus={runStatus} testId="runtime-visual-swarm" />;
  }
  return <FlowWrapper nodes={nodes} edges={edges} testId="runtime-visual-swarm" />;
}

function usesObservedAgentTrace(events: RunExecutionEvent[]) {
  return events.length === 0 || events.some((event) => event.eventFamily === "agent" || event.source === "ai_service");
}

function connectionHandles(source: Node, target: Node) {
  const dx = target.position.x - source.position.x;
  const dy = target.position.y - source.position.y;
  if (Math.abs(dx) >= Math.abs(dy) * 0.8) {
    return dx >= 0 ? {} : { sourceHandle: "reverse-out", targetHandle: "reverse-in" };
  }
  return dy >= 0
    ? { sourceHandle: "bottom-out", targetHandle: "top-in" }
    : { sourceHandle: "top-out", targetHandle: "bottom-in" };
}

function ObservedAgentFlow({ architecture, executionEvents, runStatus, testId }: {
  architecture: "centralized" | "workflow" | "swarm";
  executionEvents: RunExecutionEvent[];
  runStatus?: string | null;
  testId: string;
}) {
  const terminal = isTerminalRunStatus(runStatus);
  const { nodes, edges, height } = useMemo(() => {
    const observed = observedAgentGraph(executionEvents, terminal);
    const graph = architecture === "swarm" ? {
      agents: [
        ...SWARM_ROSTER.map((peer) => {
          const matching = observed.agents.filter((agent) => swarmRole(agent.role) === peer.id);
          return {
            role: peer.id,
            status: matching.at(-1)?.status ?? "not_invoked",
            events: matching.flatMap((agent) => agent.events).sort((a, b) => a.sequenceNo - b.sequenceNo),
          };
        }),
        ...observed.agents.filter((agent) => !SWARM_ROSTER.some((peer) => peer.id === swarmRole(agent.role))),
      ],
      links: observed.links.map((link) => ({ ...link, from: swarmRole(link.from), to: swarmRole(link.to) })),
    } : observed;
    const root = graph.agents.find(({ role }) => architecture === "swarm"
      ? /coordinator|iniciador/.test(role)
      : /supervisor/.test(role)) ?? graph.agents[0];
    const peers = graph.agents.filter((agent) => agent !== root);
    const positions = new Map<string, { x: number; y: number }>();
    if (architecture === "workflow") {
      graph.agents.forEach(({ role }, index) => positions.set(role, { x: index * 244, y: 0 }));
    } else if (architecture === "swarm") {
      graph.agents.forEach(({ role }, index) => {
        const peer = SWARM_ROSTER.find((candidate) => candidate.id === role);
        positions.set(role, peer ? { x: peer.x, y: peer.y } : { x: 792, y: (index - SWARM_ROSTER.length) * 148 });
      });
    } else {
      if (root) positions.set(root.role, { x: 0, y: Math.max(0, peers.length - 1) * 74 });
      peers.forEach(({ role }, index) => positions.set(role, { x: 292, y: index * 148 }));
    }
    const nodes = graph.agents.map((agent) => {
      const position = positions.get(agent.role) ?? { x: 0, y: 0 };
      const peer = architecture === "swarm" ? SWARM_ROSTER.find((candidate) => candidate.id === agent.role) : undefined;
      const description = architecture === "workflow"
        ? `Etapa ${graph.agents.indexOf(agent) + 1} · execução registrada`
        : peer
          ? peer.description
          : agent === root && /supervisor/.test(agent.role) ? "Coordena os especialistas" : "Agente acionado";
      const node = makeNode(agent.role, peer?.label ?? formatAgentName(agent.role), description,
        agent.status, !terminal, position.x, position.y,
        agent.status === "not_invoked" ? "muted" : undefined, agent.events.find((event) => event.nodeId)?.nodeId, undefined, agent.events);
      node.data.uniformHeight = architecture === "swarm";
      if (architecture === "workflow" && ["synthesizer", "synthesis_agent", "workflow_synthesis_agent"].includes(agent.role)) {
        node.data.incomingEvidence = synthesisEvidence(executionEvents, [agent.role]);
      }
      return node;
    });
    const byId = new Map(nodes.map((node) => [node.id, node]));
    // A reply on the same relationship is a result of that call, not a second
    // crossing route. Keep its recorded evidence in the agent detail popover.
    const connections = new Map<string, { from: string; to: string; status: string; returned: boolean; exchange: boolean; kind: "call" | "return" }>();
    for (const link of graph.links) {
      if (link.from === link.to || !byId.has(link.from) || !byId.has(link.to)) continue;
      const key = [link.from, link.to].sort().join(":");
      const previous = connections.get(key);
      const reverse = previous && previous.from === link.to && previous.to === link.from;
      if (!previous) connections.set(key, { ...link, returned: false, exchange: false });
      else if (link.kind === "call" && previous.kind !== "call") {
        connections.set(key, { ...link, returned: Boolean(reverse), exchange: false });
      } else {
        if (reverse && previous.kind === "call" && link.kind === "return") previous.returned = true;
        if (reverse && previous.kind === "return" && link.kind === "return") previous.exchange = true;
        if (link.status === "running") previous.status = "running";
      }
    }
    const edges: Edge[] = [...connections.values()].map((link) => {
      const state: EdgeState = link.status === "running" && !terminal ? "active" : "settled";
      return {
        ...makeEdge(link.from, link.to, state),
        ...connectionHandles(byId.get(link.from)!, byId.get(link.to)!),
        label: link.returned ? "Chamada e retorno registrados" : link.exchange ? "Comunicação registrada nos dois sentidos" : link.kind === "call" ? "Invocação registrada" : "Comunicação registrada",
        data: {
          state,
          swarm: architecture === "swarm",
          bidirectional: architecture !== "centralized" && (link.returned || link.exchange),
          labelText: architecture === "centralized" ? link.returned ? "retorno recebido" : link.exchange ? "troca de mensagens" : undefined : undefined,
        },
      };
    });
    if (architecture === "swarm") {
      const invoked = [...new Set(observed.agents.map((agent) => swarmRole(agent.role)))];
      for (let index = 1; index < invoked.length; index++) {
        const current = invoked[index];
        const earlier = invoked.slice(0, index);
        if (edges.some((edge) => edge.target === current && earlier.includes(edge.source)
          || edge.source === current && earlier.includes(edge.target))) continue;
        const firstEvent = graph.agents.find((agent) => agent.role === current)?.events[0]?.sequenceNo ?? Infinity;
        // Select the last completed invocation before this agent started, not
        // the roster position. This expresses order without inventing a message.
        const lastCompleted = earlier.map((role) => ({
          role,
          completedAt: graph.agents.find((agent) => agent.role === role)?.events
            .filter((event) => event.eventFamily === "agent" && event.eventName === "completed" && event.sequenceNo < firstEvent).at(-1)?.sequenceNo ?? -1,
        })).sort((a, b) => b.completedAt - a.completedAt)[0];
        const previous = lastCompleted && lastCompleted.completedAt >= 0 ? lastCompleted.role : earlier.at(-1)!;
        const state: EdgeState = byId.get(current)?.data.status === "running" && !terminal ? "active" : "settled";
        edges.push({
          ...makeEdge(previous, current, state),
          id: `${previous}-${current}-sequence`,
          label: "Ordem de execução, sem comunicação direta registrada",
          data: { state, swarm: true, sequence: true },
        });
      }
    }
    const height = architecture === "workflow" ? 300 : architecture === "swarm" ? 380 : Math.max(230, Math.min(500, peers.length * 148 + 48));
    return { nodes, edges: architecture === "workflow" ? workflowConnections(nodes) : edges, height };
  }, [architecture, executionEvents, terminal]);
  return (
    <div className="min-w-0 max-w-full" data-testid="observed-agent-flow" data-layout={architecture}>
      {nodes.length ? (
        <>
          <p className="px-2 py-1 text-xs leading-relaxed text-muted-foreground">
            {architecture === "workflow" ? "Etapas em ordem de execução. As evidências recebidas ficam nos detalhes do Sintetizador." : architecture === "swarm" ? "Todos os agentes disponíveis. Os agentes não acionados permanecem em cinza." : "Agentes e conexões registrados na execução. Retornos aparecem na mesma conexão."}
          </p>
          {architecture !== "centralized" ? (
            <div aria-label="Legenda das conexões" className="flex flex-wrap gap-x-4 gap-y-1 px-2 pb-2 text-[11px] text-muted-foreground">
              {architecture === "workflow" ? (
                <span className="inline-flex items-center gap-1.5"><span aria-hidden="true" className="text-base leading-none text-emerald-600">→</span> Ordem de execução</span>
              ) : <>
                <span className="inline-flex items-center gap-1.5"><span aria-hidden="true" className="text-base leading-none text-emerald-600">→</span> Comunicação registrada</span>
                <span className="inline-flex items-center gap-1.5"><span aria-hidden="true" className="text-base leading-none text-emerald-600">↔</span> Chamada e retorno</span>
                <span className="inline-flex items-center gap-1.5"><span aria-hidden="true" className="w-5 border-t-2 border-dashed border-current" /> Ordem de execução</span>
              </>}
            </div>
          ) : null}
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
