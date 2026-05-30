import type { ArchitectureMode } from "@/lib/types";

const ARCHITECTURE_LABELS: Record<ArchitectureMode, string> = {
  all_architectures: "Comparação das arquiteturas",
  centralized_orchestration: "Orquestração Centralizada",
  structured_workflow: "Workflow Estruturado",
  decentralized_swarm: "Swarm Descentralizado",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "Pendente",
  running: "Em andamento",
  completed: "Concluída",
  failed: "Falhou",
  cancelled: "Cancelada",
  waiting: "Aguardando",
  human_review_required: "Revisão humana",
};

const ACTOR_LABELS: Record<string, string> = {
  supervisor_agent: "Agente Supervisor",
  faq_agent: "Agente FAQ",
  stock_agent: "Agente de Estoque",
  image_intake_agent: "Agente de Anexos",
  faq_specialist: "Agente FAQ",
  stock_specialist: "Agente de Estoque",
  image_specialist: "Agente de Anexos",
  router_agent: "Agente Roteador",
  multi_modal: "Agente Multimodal",
  multi_modal_agent: "Agente Multimodal",
  multimodal_agent: "Agente Multimodal",
  swarm_coordinator: "Par Inicial (Swarm)",
  swarm_synthesizer: "Sintetizador (Swarm)",
  response_streamer: "Streamer de Resposta",
  review_agent: "Agente de Revisão",
  synthesis_agent: "Agente de Síntese",
  workflow_evidence_agent: "Agente de Evidências",
  workflow_multimodal_agent: "Agente Multimodal",
  workflow_review_agent: "Agente de Revisão",
  workflow_synthesis_agent: "Agente de Síntese",
  ai_runtime: "Runtime de IA",
  runtime: "Runtime",
};

const PHASE_LABELS: Record<string, string> = {
  dispatch: "Despacho",
  classify: "Classificação",
  gather_evidence: "Coleta de evidências",
  multimodal_analysis: "Análise multimodal",
  review_gate: "Portão de revisão",
  synthesize: "Síntese",
  specialist: "Especialista",
  workflow: "Workflow",
  swarm: "Swarm",
  handoff_loop: "Ciclo de handoff",
  completed: "Concluída",
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
