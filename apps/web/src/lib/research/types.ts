export type Json =
  | string
  | number
  | boolean
  | null
  | Json[]
  | { [key: string]: Json };
export type Architecture =
  | "centralized_orchestration"
  | "structured_workflow"
  | "decentralized_swarm";
export const labels: Record<Architecture, string> = {
  centralized_orchestration: "Centralizada",
  structured_workflow: "Workflow",
  decentralized_swarm: "Swarm",
};
export const dimensions: Record<string, string> = {
  intent_adherence: "Aderência à intenção",
  operational_correctness: "Correção do conteúdo",
  safety: "Segurança",
  completeness: "Completude",
  clarity: "Clareza",
};
export interface ResearchRow {
  unit_id: string;
  run_id: string;
  scenario_id: string;
  architecture: Architecture;
  repetition: number;
  stratum: string;
  difficulty: string;
  status: string;
  task_success: boolean | null;
  content_success: boolean | null;
  procedure_compliance: boolean | null;
  procedure_applicable: boolean;
  end_to_end_latency_ms: number;
  latency_ms: number;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  model_requests: number;
  domain_tool_calls: number;
  coordination_tool_calls: number;
  agent_invocations: number;
  handoffs_requested: number;
  handoffs_completed: number;
  handoffs_failed: number;
  expected_resolution_mode: string;
  judge_valid: boolean;
  quality: Record<string, number> | null;
  input_excerpt: string;
}
export interface ResearchEvent {
  sequence: number;
  recorded_at: string;
  eventFamily: string;
  eventName: string;
  status: string;
  actorName: string | null;
  nodeId: string | null;
  toolName: string | null;
  durationMs: number | null;
  payload: Json;
}
export interface ResearchDetail {
  record: ResearchRow;
  input: { text: string | null; history: Json; attachments: Json };
  final_text: string;
  evaluation: {
    criteria: {
      criterion_id: string;
      met: boolean;
      reason: string;
      evidence_refs: Json;
    }[];
    quality: Record<string, number>;
    quality_reasons: Record<string, string>;
    [key: string]: Json;
  } | null;
  objective_checks: Json;
  events: ResearchEvent[];
  gold: Json;
  initial_input_sha256: string | null;
  source_hashes: Record<string, string>;
}
export interface ResearchData {
  plan: string;
  experiment_id: string;
  dataset: string;
  manifest_sha256: string;
  rows: ResearchRow[];
  resources: Json;
  source_transport: string;
  loaded_at: string;
  storage: "memory";
}
