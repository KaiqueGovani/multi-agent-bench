// Imported only by server routes. No runtime, AWS SDK, API client or database dependency.
import "server-only";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import type {
  Json,
  ResearchData,
  ResearchDetail,
  ResearchEvent,
  ResearchRow,
} from "./types";

const expectedManifest =
  "921b54f9310e3281c519e5b61100304aa3a4755a27daf0238a96c3910f4cf208";
const loopback = new Set(["127.0.0.1", "::1", "::ffff:127.0.0.1"]);
type RequestHeaders = Pick<Headers, "get">;
type ReportHandle = {
  type: string;
  is_active: boolean;
  localEndpoint?: { ip4?: string; ip6?: string; port?: number } | null;
  remoteEndpoint?: unknown;
};
let replayPorts: Set<number> | undefined;

function loopbackListenerPorts(): Set<number> {
  if (replayPorts) return replayPorts;
  replayPorts = new Set();
  try {
    // Host and forwarding headers alone are caller-controlled. Inspect the
    // actual listener once per process, without writing or logging the report.
    const report = process.report?.getReport() as
      | { libuv?: ReportHandle[] }
      | undefined;
    const listeners = report?.libuv?.filter(
      (handle) => handle.type === "tcp" && handle.is_active && handle.remoteEndpoint === null,
    ) ?? [];
    const ports = new Set<number>();
    for (const { localEndpoint } of listeners) {
      if (
        typeof localEndpoint?.port !== "number" ||
        !loopback.has(localEndpoint.ip4 ?? localEndpoint.ip6 ?? "")
      ) return replayPorts;
      ports.add(localEndpoint.port);
    }
    replayPorts = ports;
  } catch {
    // An unavailable or unsupported diagnostic format keeps replay disabled.
  }
  return replayPorts;
}

export function canAccessPrivateReplay(headers: RequestHeaders): boolean {
  if (process.env.MAB_ENABLE_PRIVATE_REPLAY !== "1") return false;
  const host = headers.get("host")?.toLowerCase() ?? "";
  const match = /^(?:localhost|127\.0\.0\.1|\[::1\])(?::(\d{1,5}))?$/.exec(host);
  if (!match || headers.get("forwarded") !== null) return false;
  const forwardedHost = headers.get("x-forwarded-host")?.toLowerCase();
  if (forwardedHost && forwardedHost !== host) return false;
  if (!loopback.has(headers.get("x-forwarded-for") ?? "")) return false;
  const protocol = headers.get("x-forwarded-proto") ?? "http";
  if (protocol !== "http" && protocol !== "https") return false;
  const site = headers.get("sec-fetch-site");
  if (site && site !== "same-origin" && site !== "none") return false;
  const origin = headers.get("origin");
  if (origin && origin !== `${protocol}://${host}`) return false;
  const port = match[1] ? Number(match[1]) : protocol === "https" ? 443 : 80;
  return loopbackListenerPorts().has(port);
}

const fields = [
  "unit_id",
  "run_id",
  "scenario_id",
  "architecture",
  "repetition",
  "stratum",
  "difficulty",
  "status",
  "task_success",
  "content_success",
  "procedure_compliance",
  "procedure_applicable",
  "end_to_end_latency_ms",
  "latency_ms",
  "total_tokens",
  "input_tokens",
  "output_tokens",
  "model_requests",
  "domain_tool_calls",
  "coordination_tool_calls",
  "agent_invocations",
  "handoffs_requested",
  "handoffs_completed",
  "handoffs_failed",
  "expected_resolution_mode",
];
const source = () =>
  path.resolve(
    process.env.MAB_REPLAY_SOURCE ??
      path.join(
        process.cwd(),
        "../../var/reports/real-conversations-v1/matrix40-v1-final",
      ),
  );
const hash = (text: string) => createHash("sha256").update(text).digest("hex");
// Curated cases already contain participant aliases. Defensive redaction is applied
// to the in-memory display copy only, including JSON serialized inside tool results.
function redact(value: Json): Json {
  if (Array.isArray(value)) return value.map(redact);
  if (value && typeof value === "object")
    return Object.fromEntries(
      Object.entries(value)
        .filter(
          ([key]) =>
            !/api.?key|secret|authorization|cookie|retrieval.?url|storage.?key|account|conversation.?id|correlation.?id|message.?id/i.test(
              key,
            ),
        )
        .map(([key, item]) => [key, redact(item)]),
    );
  if (typeof value !== "string") return value;
  // UUIDs and numeric measurements are preserved; contacts are suppressed.
  return value
    .replace(
      /https?:\/\/[^\s"<>]+|[\w.+-]+@[\w.-]+\.[a-z]{2,}/gi,
      "[Contato removido]",
    )
    .replace(
      /(?<![\w-])(?:\+55\s*)?(?:\(?\d{2}\)?[ -]*)?\d{4,5}[ -]\d{4}(?![\w-])/g,
      "[Telefone removido]",
    );
}

type Store = { data: ResearchData; details: Map<string, ResearchDetail> };
const globalStore = globalThis as typeof globalThis & {
  mabResearchMemory?: Promise<Store>;
};
export function getResearchMemory(headers: RequestHeaders): Promise<Store> | null {
  if (!canAccessPrivateReplay(headers)) return null;
  // One immutable snapshot per server process. A failed load can be retried.
  if (!globalStore.mabResearchMemory)
    globalStore.mabResearchMemory = load().catch((error) => {
      delete globalStore.mabResearchMemory;
      throw error;
    });
  return globalStore.mabResearchMemory;
}

async function load(): Promise<Store> {
  const base = source();
  const manifestText = await readFile(path.join(base, "manifest.json"), "utf8");
  if (hash(manifestText) !== expectedManifest)
    throw new Error("Manifesto diferente do lote congelado.");
  const manifest = JSON.parse(manifestText);
  const originals = (
    await readFile(path.join(base, "aggregated-evaluations.jsonl"), "utf8")
  )
    .trim()
    .split("\n")
    .map((line) => JSON.parse(line));
  if (
    originals.length !== 600 ||
    new Set(originals.map((r) => r.unit_id)).size !== 600 ||
    new Set(originals.map((r) => r.run_id)).size !== 600
  )
    throw new Error("Lote incompleto ou duplicado.");
  const details = new Map<string, ResearchDetail>();
  // Bounded filesystem reads. Everything needed for inspection is retained in RAM.
  for (let offset = 0; offset < originals.length; offset += 20) {
    await Promise.all(
      originals.slice(offset, offset + 20).map(async (original) => {
        if (!/^[a-f0-9-]{36}$/.test(original.unit_id))
          throw new Error("Identificador inválido.");
        const folder = path.join(base, original.unit_id);
        const [taskText, eventsText, resultText] = await Promise.all(
          ["task.json", "events.jsonl", "result.json"].map((name) =>
            readFile(path.join(folder, name), "utf8"),
          ),
        );
        const task = JSON.parse(taskText).case;
        const events = eventsText
          .trim()
          .split("\n")
          .map((line) => JSON.parse(line));
        const input = redact({
          text: task.text ?? null,
          history: task.history ?? [],
          attachments: task.attachments ?? [],
        }) as ResearchDetail["input"];
        const record = {
          ...Object.fromEntries(
            fields.map((key) => [key, original[key] ?? null]),
          ),
          judge_valid: original.evaluation !== null,
          quality: original.evaluation?.quality ?? null,
          input_excerpt: input.text ?? "Entrada multimodal",
        } as ResearchRow;
        const selectedEvents = events
          .filter((e) => e.eventFamily !== "experiment")
          .map((e) =>
            redact(
              Object.fromEntries(
                [
                  "sequence",
                  "recorded_at",
                  "eventFamily",
                  "eventName",
                  "status",
                  "actorName",
                  "nodeId",
                  "toolName",
                  "durationMs",
                  "payload",
                ].map((key) => [key, e[key] ?? null]),
              ) as Json,
            ),
          ) as unknown as ResearchEvent[];
        details.set(record.run_id, {
          record,
          input,
          final_text: redact(original.final_text) as string,
          evaluation: redact(
            original.evaluation,
          ) as ResearchDetail["evaluation"],
          objective_checks: redact(original.objective_checks),
          gold: redact(
            Object.fromEntries(
              [
                "essential_requirements",
                "required_evidence",
                "optional_evidence",
                "evidence_requirements",
                "expected_facts",
                "professional_review_required",
                "transfer_required",
                "acceptable_alternatives",
                "milestones",
                "critical_restrictions",
                "prohibited_behaviors",
              ].map((key) => [key, task[key] ?? null]),
            ),
          ),
          events: selectedEvents,
          initial_input_sha256:
            events.find(
              (e) => e.eventFamily === "agent" && e.eventName === "started",
            )?.payload.inputSha256 ?? null,
          source_hashes: {
            "task.json": hash(taskText),
            "events.jsonl": hash(eventsText),
            "result.json": hash(resultText),
          },
        });
      }),
    );
  }
  const rows = originals.map(
    (original) => details.get(original.run_id)!.record,
  );
  if (
    rows.filter((r) => r.task_success === true).length !== 356 ||
    rows.filter((r) => r.task_success === false).length !== 244 ||
    rows.filter((r) => r.judge_valid).length !== 599
  )
    throw new Error("Reconciliação do lote falhou.");
  return {
    details,
    data: {
      plan: "matrix40-v1-final",
      experiment_id: manifest.experiment_id,
      dataset: manifest.dataset_version,
      manifest_sha256: hash(manifestText),
      rows,
      resources: JSON.parse(
        await readFile(path.join(base, "resource-consumption.json"), "utf8"),
      ),
      source_transport: "Processos e arquivos · direct-core-runtime",
      loaded_at: new Date().toISOString(),
      storage: "memory",
    },
  };
}
