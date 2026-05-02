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
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { memo, useMemo } from "react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import type { RunExecutionEvent } from "@/lib/types";

// ---------------------------------------------------------------------------
// Shared types
// ---------------------------------------------------------------------------

type EdgeState = "idle" | "recent" | "active";

interface AgentNodeData {
  actorName: string;
  description: string;
  status: string;
  active: boolean;
  tone?: BadgeProps["variant"];
  nodeId?: string | null;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Custom node
// ---------------------------------------------------------------------------

const AgentNode = memo(function AgentNode({ data }: NodeProps<Node<AgentNodeData>>) {
  const { actorName, description, status, active, tone, nodeId } = data;

  return (
    <div
      className={`rounded-2xl border px-4 py-3 shadow-sm transition-colors min-w-[140px] max-w-[180px] ${
        active
          ? "border-primary/60 bg-primary/10 ring-2 ring-primary/20"
          : status === "completed"
            ? "border-emerald-200 bg-emerald-50/80"
            : tone === "muted"
              ? "border-dashed border-border/70 bg-muted/20"
              : "border-border bg-background"
      }`}
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
                    : "bg-muted-foreground/50"
          }`}
        />
        <p className="text-sm font-semibold truncate">{actorName}</p>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">{description}</p>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <Badge variant={tone ?? statusBadgeVariant(status)}>{status}</Badge>
        {nodeId ? (
          <span className="truncate text-[11px] text-muted-foreground">{nodeId}</span>
        ) : null}
      </div>
    </div>
  );
});

// ---------------------------------------------------------------------------
// Custom animated edge
// ---------------------------------------------------------------------------

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

  const color = state === "active" ? "#007f5f" : state === "recent" ? "#1f9d61" : "#c5d0de";
  const strokeWidth = state === "active" ? 2.5 : state === "recent" ? 1.8 : 1;
  const animated = state !== "idle";

  return (
    <>
      <BaseEdge
        path={edgePath}
        style={{
          stroke: color,
          strokeWidth,
          opacity: state === "idle" ? 0.35 : 0.85,
        }}
      />
      {animated && (
        <circle r="3" fill={color}>
          <animateMotion dur={state === "active" ? "1.5s" : "2.5s"} repeatCount="indefinite" path={edgePath} />
        </circle>
      )}
    </>
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
    <div style={{ height }} data-testid={testId}>
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
  supervisor_agent: "Agente Supervisor",
  faq_agent: "Agente FAQ",
  stock_agent: "Agente Estoque",
  image_intake_agent: "Agente Imagem",
  router_agent: "Agente Roteador",
  swarm_coordinator: "Coordenador",
  swarm_synthesizer: "Sintetizador",
  response_streamer: "Streamer de Resposta",
};

function formatAgentName(name: string): string {
  return AGENT_NAME_MAP[name] ?? name;
}

function statusBadgeVariant(status: string): BadgeProps["variant"] {
  if (status === "completed") return "success";
  if (status === "running") return "warning";
  if (status === "failed" || status === "human_review_required") return "destructive";
  if (status === "pending") return "muted";
  return "outline";
}

function getActorName(value: unknown): string | null {
  if (!value || typeof value !== "object") return null;
  const raw = (value as Record<string, unknown>).actorName;
  return typeof raw === "string" ? raw : null;
}

function getStatus(value: unknown): string {
  if (!value || typeof value !== "object") return "pending";
  const raw = (value as Record<string, unknown>).status ?? (value as Record<string, unknown>).lastStatus;
  return typeof raw === "string" ? raw : "pending";
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
): Node<AgentNodeData> {
  return {
    id,
    type: "agent",
    position: { x, y },
    data: { actorName, description, status, active, tone, nodeId },
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

/**
 * Derive edge state from runtime events for a specific source→target connection.
 * - "active": an event with status "running" exists where the actor matches source or target
 * - "recent": a recent event with status "completed" exists on this connection
 * - "idle": no relevant activity on this connection
 */
function edgeStateFromEvents(
  events: RunExecutionEvent[],
  source: string,
  target: string,
): EdgeState {
  // Check the last N events for activity on this connection
  const recent = events.slice(-10);
  for (let i = recent.length - 1; i >= 0; i--) {
    const e = recent[i];
    const actor = e.actorName;
    if (!actor) continue;

    // Handoff events: payload.from→payload.to or payload.targetActor
    if (e.eventFamily === "handoff") {
      const p = e.payload as Record<string, unknown>;
      const from = p.from as string | undefined;
      const to = (p.to ?? p.targetActor) as string | undefined;
      if ((from === source && to === target) || (actor === source && to === target)) {
        return e.status === "running" ? "active" : "recent";
      }
    }

    // Node/tool events: actor matches the target node of the edge (source is sending to target)
    if (e.eventFamily === "node" || e.eventFamily === "tool") {
      if (actor === target) {
        return e.status === "running" ? "active" : e.status === "completed" ? "recent" : "idle";
      }
    }

    // Response events: actor is response_streamer → edges into response_streamer activate
    if (e.eventFamily === "response" && actor === target) {
      return e.status === "running" ? "active" : e.status === "completed" ? "recent" : "idle";
    }
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
}: {
  activeActorName: string;
  actors: unknown[];
  executionEvents: RunExecutionEvent[];
}) {
  const { nodes, edges } = useMemo(() => {
    const findActor = (name: string) => actors.find((a) => getActorName(a) === name);

    const sup = findActor("supervisor_agent");
    const supStatus = getStatus(sup);
    const supActive = "supervisor_agent" === activeActorName;

    const specialists = [
      { name: "faq_agent", desc: "FAQ e contexto geral", y: 0 },
      { name: "stock_agent", desc: "estoque e disponibilidade", y: 130 },
      { name: "image_intake_agent", desc: "imagem ou documento", y: 260 },
    ];

    const respActor = findActor("response_streamer");
    const respStatus = getStatus(respActor);
    const respActive = "response_streamer" === activeActorName;

    const nodes: Node<AgentNodeData>[] = [
      makeNode("supervisor_agent", "Agente Supervisor", "orquestra e roteia", supStatus, supActive, 0, 130, "info", getNodeId(sup)),
      ...specialists.map((s) => {
        const actor = findActor(s.name);
        return makeNode(s.name, formatAgentName(s.name), s.desc, getStatus(actor), s.name === activeActorName, 280, s.y, undefined, getNodeId(actor));
      }),
      makeNode("response_streamer", "Streamer de Resposta", "sintetiza a resposta", respStatus, respActive, 560, 130, undefined, getNodeId(respActor)),
    ];

    const edges: Edge[] = [
      ...specialists.map((s) =>
        makeEdge("supervisor_agent", s.name, edgeStateFromEvents(executionEvents, "supervisor_agent", s.name)),
      ),
      ...specialists.map((s) =>
        makeEdge(s.name, "response_streamer", edgeStateFromEvents(executionEvents, s.name, "response_streamer")),
      ),
    ];

    return { nodes, edges };
  }, [activeActorName, actors, executionEvents]);

  return <FlowWrapper nodes={nodes} edges={edges} testId="runtime-visual-centralized" height={360} />;
}

// ---------------------------------------------------------------------------
// WorkflowFlow
// ---------------------------------------------------------------------------

export function WorkflowFlow({
  activeActorName,
  stages,
  executionEvents,
}: {
  activeActorName: string;
  stages: unknown[];
  executionEvents: RunExecutionEvent[];
}) {
  const { nodes, edges } = useMemo(() => {
    const sequence = [
      { stage: "classify", actor: "router_agent", desc: "Classificar intenção" },
      { stage: "gather_evidence", actor: "workflow_evidence_agent", desc: "Coletar Evidências" },
      { stage: "multimodal_analysis", actor: "workflow_multimodal_agent", desc: "Análise Multimodal" },
      { stage: "review_gate", actor: "workflow_review_agent", desc: "Portão de Revisão" },
      { stage: "synthesize", actor: "workflow_synthesis_agent", desc: "Sintetizar saída" },
    ];

    const nodes: Node<AgentNodeData>[] = sequence.map((step, i) => {
      const matching = stages.filter((s) => getStage(s) === step.stage).at(-1);
      const actorName = getActorName(matching) ?? step.actor;
      const status = getStatus(matching);
      const active = actorName === activeActorName;
      const tone: BadgeProps["variant"] | undefined = matching ? undefined : "muted";
      return makeNode(step.actor, actorName, step.desc, status, active, i * 200, 0, tone, getNodeId(matching));
    });

    const edges: Edge[] = nodes.slice(0, -1).map((n, i) => {
      const next = nodes[i + 1];
      return makeEdge(n.id, next.id, edgeStateFromEvents(executionEvents, n.data.actorName, next.data.actorName));
    });

    return { nodes, edges };
  }, [activeActorName, stages, executionEvents]);

  return <FlowWrapper nodes={nodes} edges={edges} testId="runtime-visual-workflow" height={300} />;
}

// ---------------------------------------------------------------------------
// SwarmFlow
// ---------------------------------------------------------------------------

export function SwarmFlow({
  activeActorName,
  actors,
  executionEvents,
  handoffs,
}: {
  activeActorName: string;
  actors: unknown[];
  executionEvents: RunExecutionEvent[];
  handoffs: unknown[];
}) {
  const { nodes, edges } = useMemo(() => {
    const findActor = (name: string) => actors.find((a) => getActorName(a) === name);
    const coordActor = actors.find((a) => getActorName(a)?.includes("coordinator"));
    const coordName = getActorName(coordActor) ?? "swarm_coordinator";
    const coordStatus = getStatus(coordActor);
    const coordActive = coordName === activeActorName;

    const specialistDefs = [
      { name: "faq_agent", desc: "especialista", y: 0 },
      { name: "stock_agent", desc: "especialista", y: 130 },
      { name: "image_intake_agent", desc: "especialista", y: 260 },
    ];

    const synthActor = findActor("swarm_synthesizer");
    const synthStatus = getStatus(synthActor);
    const synthActive = "swarm_synthesizer" === activeActorName;

    const nodes: Node<AgentNodeData>[] = [
      makeNode(coordName, formatAgentName(coordName), "coordena as transferências", coordStatus, coordActive, 0, 130, "info", getNodeId(coordActor)),
      ...specialistDefs.map((s) => {
        const actor = findActor(s.name);
        return makeNode(s.name, formatAgentName(s.name), s.desc, getStatus(actor), s.name === activeActorName, 260, s.y, undefined, getNodeId(actor));
      }),
      makeNode("swarm_synthesizer", "Sintetizador", "síntese final", synthStatus, synthActive, 520, 130, undefined, getNodeId(synthActor)),
    ];

    const edges: Edge[] = [
      ...specialistDefs.map((s) =>
        makeEdge(coordName, s.name, edgeStateFromEvents(executionEvents, coordName, s.name)),
      ),
      ...specialistDefs.map((s) =>
        makeEdge(s.name, "swarm_synthesizer", edgeStateFromEvents(executionEvents, s.name, "swarm_synthesizer")),
      ),
    ];

    return { nodes, edges };
  }, [activeActorName, actors, executionEvents, handoffs]);

  return <FlowWrapper nodes={nodes} edges={edges} testId="runtime-visual-swarm" height={360} />;
}
