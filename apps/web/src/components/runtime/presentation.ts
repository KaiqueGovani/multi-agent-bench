import type { ArchitectureMode } from "@/lib/types";

const ARCHITECTURE_LABELS: Record<ArchitectureMode, string> = {
  all_architectures: "Comparacao das arquiteturas",
  centralized_orchestration: "Orquestracao Centralizada",
  structured_workflow: "Workflow Estruturado",
  decentralized_swarm: "Swarm Descentralizado",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "Pendente",
  running: "Em andamento",
  completed: "Concluida",
  failed: "Falhou",
  cancelled: "Cancelada",
  waiting: "Aguardando",
  human_review_required: "Revisao humana",
};

const ACTOR_LABELS: Record<string, string> = {
  supervisor_agent: "Agente Supervisor",
  faq_agent: "Agente FAQ",
  stock_agent: "Agente de Estoque",
  image_intake_agent: "Agente de Anexos",
  router_agent: "Agente Roteador",
  swarm_coordinator: "Coordenador do Swarm",
  swarm_synthesizer: "Sintetizador do Swarm",
  response_streamer: "Streamer de Resposta",
  review_agent: "Agente de Revisao",
  synthesis_agent: "Agente de Sintese",
  workflow_evidence_agent: "Agente de Evidencias",
  workflow_multimodal_agent: "Agente Multimodal",
  workflow_review_agent: "Agente de Revisao",
  workflow_synthesis_agent: "Agente de Sintese",
  ai_runtime: "Runtime de IA",
  runtime: "Runtime",
};

const PHASE_LABELS: Record<string, string> = {
  dispatch: "Despacho",
  classify: "Classificacao",
  gather_evidence: "Coleta de evidencias",
  multimodal_analysis: "Analise multimodal",
  review_gate: "Portao de revisao",
  synthesize: "Sintese",
  specialist: "Especialista",
  workflow: "Workflow",
  swarm: "Swarm",
  handoff_loop: "Ciclo de handoff",
  completed: "Concluida",
};

export function formatArchitectureLabel(mode: ArchitectureMode | string): string {
  return ARCHITECTURE_LABELS[mode as ArchitectureMode] ?? humanizeToken(mode);
}

export function formatStatusLabel(status: string | null | undefined): string {
  if (!status) {
    return "n/a";
  }
  return STATUS_LABELS[status] ?? humanizeToken(status);
}

export function formatActorLabel(actorName: string | null | undefined): string {
  if (!actorName) {
    return "Runtime";
  }
  return ACTOR_LABELS[actorName] ?? humanizeToken(actorName);
}

export function formatPhaseLabel(phase: string | null | undefined): string {
  if (!phase) {
    return "n/a";
  }
  return PHASE_LABELS[phase] ?? humanizeToken(phase);
}

function humanizeToken(value: string): string {
  return value
    .replaceAll(".", " ")
    .replaceAll("_", " ")
    .trim()
    .replace(/\b\w/g, (match) => match.toUpperCase());
}
