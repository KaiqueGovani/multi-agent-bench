"use client";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { BarChart3, Download, ShieldCheck } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MarkdownContent } from "@/components/common/markdown-content";
import {
  labels,
  dimensions,
  type Architecture,
  type Json,
  type ResearchData,
  type ResearchDetail,
  type ResearchRow,
} from "@/lib/research/types";

const archs = Object.keys(labels) as Architecture[];
const strata: Record<string, string> = {
  stock: "Estoque",
  faq: "FAQ",
  professional_review: "Encaminhamento profissional",
  attachments: "Anexos",
  continuity: "Continuidade",
};
const difficulties: Record<string, string> = {
  low: "Baixa",
  medium: "Média",
  high: "Alta",
};
const modes: Record<string, string> = {
  request_information: "Pedir informação",
  capability_limit: "Declarar limitação",
  controlled_fact: "Responder com fatos controlados",
  controlled_fact_and_limit: "Fatos controlados e limitação",
  professional_referral: "Encaminhamento profissional",
  professional_referral_and_limit: "Encaminhamento e limitação",
  professional_referral_and_clarification: "Encaminhamento e esclarecimento",
};
const num = (v: number) =>
  v.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
const duration = (ms: number) => `${num(ms / 1000)} s`;
const result = (v: boolean | null) =>
  v === true ? "Sucesso" : v === false ? "Falha" : "Desconhecido";
const conformity = (v: boolean | null) =>
  v === true ? "Cumprido" : v === false ? "Não cumprido" : "Ausente";
const median = (values: number[]) => {
  const v = [...values].sort((a, b) => a - b);
  return v.length
    ? (v[Math.floor((v.length - 1) / 2)] + v[Math.floor(v.length / 2)]) / 2
    : 0;
};
function caseMedian(
  rows: ResearchRow[],
  key: "total_tokens" | "end_to_end_latency_ms",
) {
  return median(
    [...new Set(rows.map((r) => r.scenario_id))].map((s) =>
      median(rows.filter((r) => r.scenario_id === s).map((r) => r[key])),
    ),
  );
}
async function read<T>(url: string, signal?: AbortSignal): Promise<T> {
  const r = await fetch(url, { signal, cache: "no-store" });
  const body = await r.json();
  if (!r.ok) throw new Error(body.error ?? "Consulta indisponível.");
  return body as T;
}

export function ResearchWorkspace() {
  const [data, setData] = useState<ResearchData | null>(null),
    [error, setError] = useState<string | null>(null),
    [retry, setRetry] = useState(0);
  const [tab, setTab] = useState("overview"),
    [search, setSearch] = useState(""),
    [architecture, setArchitecture] = useState(""),
    [stratum, setStratum] = useState(""),
    [difficulty, setDifficulty] = useState(""),
    [outcome, setOutcome] = useState(""),
    [judge, setJudge] = useState(""),
    [mode, setMode] = useState(""),
    [sort, setSort] = useState("order"),
    [page, setPage] = useState(0);
  const [selected, setSelected] = useState<string | null>(null),
    [detail, setDetail] = useState<ResearchDetail | null>(null),
    [detailError, setDetailError] = useState<string | null>(null),
    [detailTab, setDetailTab] = useState("conversation"),
    [peers, setPeers] = useState<ResearchDetail[]>([]);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    const c = new AbortController();
    setError(null);
    void read<ResearchData>("/api/research", c.signal)
      .then(setData)
      .catch((e) => {
        if (!c.signal.aborted) setError(e.message);
      });
    return () => c.abort();
  }, [retry]);
  useEffect(() => {
    const sync = () => {
      const id = new URLSearchParams(location.search).get("run");
      setSelected(id);
      if (id) setTab("runs");
    };
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);
  useEffect(() => {
    setDetail(null);
    setPeers([]);
    setDetailError(null);
    if (!selected) return;
    const c = new AbortController();
    void read<ResearchDetail>(
      `/api/research?run=${encodeURIComponent(selected)}`,
      c.signal,
    )
      .then((d) => {
        setDetail(d);
        if (data)
          void Promise.all(
            data.rows
              .filter(
                (r) =>
                  r.scenario_id === d.record.scenario_id &&
                  r.repetition === d.record.repetition,
              )
              .map((r) =>
                read<ResearchDetail>(`/api/research?run=${r.run_id}`, c.signal),
              ),
          )
            .then(setPeers)
            .catch((e) => {
              if (!c.signal.aborted) setDetailError(e.message);
            });
      })
      .catch((e) => {
        if (!c.signal.aborted) setDetailError(e.message);
      });
    return () => c.abort();
  }, [selected, data, retry]);
  useEffect(() => {
    if (detail) heading.current?.focus();
  }, [detail]);
  useEffect(
    () => setPage(0),
    [search, architecture, stratum, difficulty, outcome, judge, mode, sort],
  );
  const filtered = useMemo(() => {
    const rows = (data?.rows ?? []).filter(
      (r) =>
        (!architecture || r.architecture === architecture) &&
        (!stratum || r.stratum === stratum) &&
        (!difficulty || r.difficulty === difficulty) &&
        (!mode || r.expected_resolution_mode === mode) &&
        (!outcome || result(r.task_success) === outcome) &&
        (!judge || r.judge_valid === (judge === "valid")) &&
        `${r.scenario_id} ${r.run_id} ${r.unit_id} ${r.input_excerpt}`
          .toLocaleLowerCase("pt-BR")
          .includes(search.toLocaleLowerCase("pt-BR")),
    );
    if (sort === "latency")
      rows.sort((a, b) => b.end_to_end_latency_ms - a.end_to_end_latency_ms);
    if (sort === "tokens") rows.sort((a, b) => b.total_tokens - a.total_tokens);
    if (sort === "scenario")
      rows.sort(
        (a, b) =>
          a.scenario_id.localeCompare(b.scenario_id) ||
          a.repetition - b.repetition,
      );
    return rows;
  }, [
    data,
    search,
    architecture,
    stratum,
    difficulty,
    mode,
    outcome,
    judge,
    sort,
  ]);
  function selectRun(id: string | null) {
    const url = new URL(location.href);
    if (id) url.searchParams.set("run", id);
    else url.searchParams.delete("run");
    history.pushState(null, "", url);
    setSelected(id);
    setDetailTab("conversation");
    setTab("runs");
  }
  function clear() {
    setSearch("");
    setArchitecture("");
    setStratum("");
    setDifficulty("");
    setOutcome("");
    setJudge("");
    setMode("");
    setSort("order");
  }
  function exportCsv() {
    const keys: (keyof ResearchRow)[] = [
      "unit_id",
      "scenario_id",
      "architecture",
      "repetition",
      "task_success",
      "judge_valid",
      "end_to_end_latency_ms",
      "input_tokens",
      "output_tokens",
      "total_tokens",
      "model_requests",
    ];
    const url = URL.createObjectURL(
      new Blob(
        [
          [
            keys.join(","),
            ...filtered.map((r) =>
              keys.map((k) => JSON.stringify(r[k])).join(","),
            ),
          ].join("\n"),
        ],
        { type: "text/csv;charset=utf-8" },
      ),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "MAB-metricas-filtradas.csv";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const index = filtered.findIndex((r) => r.run_id === selected);
  return (
    <main
      className="min-h-screen bg-background text-foreground"
      data-testid="research-workspace"
    >
      <a
        href="#research-main"
        className="sr-only focus:not-sr-only focus:block focus:p-3"
      >
        Ir para os resultados
      </a>
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-5">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <BarChart3 className="h-7 w-7 text-primary" />
              <h1 className="text-xl font-semibold">
                MAB · Resultados da pesquisa
              </h1>
              <Badge variant="outline">Consulta em memória</Badge>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              matrix40-v1-final · 40 cenários · 3 arquiteturas · 5 repetições
            </p>
          </div>
          <Link
            href="/"
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            Chat da POC
          </Link>
        </div>
      </header>
      <div className="mx-auto max-w-7xl px-4 py-5">
        <div className="mb-5 flex gap-3 rounded-xl border border-primary/20 bg-primary/5 p-4 text-sm">
          <ShieldCheck className="h-5 w-5 shrink-0 text-primary" />
          <p>
            <strong>Lote real preservado, somente leitura.</strong> Consulta das
            execuções existentes, sem chamar agentes ou juiz. A coleta ocorreu
            por processos e arquivos. Avaliação técnica, sem validação
            farmacêutica.
          </p>
        </div>
        <nav
          aria-label="Resultados da pesquisa"
          className="mb-5 flex flex-wrap gap-2"
        >
          {[
            ["overview", "Visão geral"],
            ["runs", "600 execuções"],
            ["scenarios", "40 cenários"],
            ["quality", "Qualidade e consumo"],
          ].map(([key, label]) => (
            <Button
              key={key}
              aria-current={tab === key ? "page" : undefined}
              variant={tab === key ? "default" : "outline"}
              onClick={() => setTab(key)}
            >
              {label}
            </Button>
          ))}
        </nav>
        <div id="research-main">
          {error ? (
            <div
              role="alert"
              className="rounded-xl border border-destructive p-5"
            >
              <p>{error}</p>
              <Button className="mt-3" onClick={() => setRetry((v) => v + 1)}>
                Tentar novamente
              </Button>
            </div>
          ) : !data ? (
            <p role="status" className="py-12 text-center">
              Carregando o lote em memória…
            </p>
          ) : (
            <>
              {tab === "overview" && (
                <div className="space-y-5">
                  <section
                    className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
                    aria-label="Totais da coleta"
                  >
                    <Metric
                      label="Conclusão técnica"
                      value="600 / 600"
                      note="Processos concluídos"
                    />
                    <Metric
                      label="Sucesso da tarefa"
                      value="356 / 600"
                      note="59,3% · 244 falhas · zero desconhecidos"
                    />
                    <Metric
                      label="Juiz principal válido"
                      value="599 / 600"
                      note="Um julgamento inválido preservado"
                    />
                    <Metric
                      label="Tokens da geração"
                      value={num(
                        data.rows.reduce((s, r) => s + r.total_tokens, 0),
                      )}
                      note="2.123 chamadas de modelo"
                    />
                  </section>
                  <Panel title="Comparação das arquiteturas">
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[680px] text-left text-sm">
                        <caption className="sr-only">
                          Resultados por arquitetura. Medianas das 40 medianas
                          por cenário.
                        </caption>
                        <thead>
                          <tr>
                            {[
                              "Arquitetura",
                              "Unidades",
                              "Sucesso da tarefa",
                              "Juiz válido",
                              "Latência e2e",
                              "Tokens",
                            ].map((x) => (
                              <th className="p-3" key={x}>
                                {x}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {archs.map((a) => {
                            const rows = data.rows.filter(
                              (r) => r.architecture === a,
                            );
                            return (
                              <tr key={a} className="border-t">
                                <th className="p-3 font-medium">{labels[a]}</th>
                                <td className="p-3">{rows.length}</td>
                                <td className="p-3">
                                  {rows.filter((r) => r.task_success).length} /
                                  200 (
                                  {num(
                                    rows.filter((r) => r.task_success).length /
                                      2,
                                  )}
                                  %)
                                </td>
                                <td className="p-3">
                                  {rows.filter((r) => r.judge_valid).length} /
                                  200
                                </td>
                                <td className="p-3">
                                  {duration(
                                    caseMedian(rows, "end_to_end_latency_ms"),
                                  )}
                                </td>
                                <td className="p-3">
                                  {num(caseMedian(rows, "total_tokens"))}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                    <p className="mt-3 text-xs text-muted-foreground">
                      Latência e tokens: mediana das 40 medianas por cenário,
                      cada uma com cinco repetições. e2e = tempo total do
                      subprocesso.
                    </p>
                  </Panel>
                  <div className="grid gap-5 md:grid-cols-2">
                    <Panel title="Como interpretar o sucesso">
                      <p className="text-sm leading-6">
                        Em 25 dos 40 cenários, a resolução esperada é pedir
                        informação ou declarar uma limitação. Sucesso no
                        gabarito não equivale a venda ou entrega concluída.
                        Conteúdo, procedimento obrigatório, qualidade e
                        encaminhamento estão separados na inspeção.
                      </p>
                    </Panel>
                    <Panel title="Julgamento ausente preservado">
                      <p className="text-sm leading-6">
                        R-faq-05 · Workflow · repetição 2: saída do juiz
                        inválida. A falha objetiva de evidência obrigatória
                        permanece registrada; as notas de qualidade estão
                        ausentes.
                      </p>
                      <Button
                        className="mt-3"
                        variant="outline"
                        onClick={() =>
                          selectRun(
                            data.rows.find((r) => !r.judge_valid)!.run_id,
                          )
                        }
                      >
                        Inspecionar esse registro
                      </Button>
                    </Panel>
                  </div>
                  <details className="rounded-xl border bg-card p-4">
                    <summary className="cursor-pointer font-medium">
                      Proveniência e limites da visualização
                    </summary>
                    <JsonView
                      value={{
                        experiment_id: data.experiment_id,
                        manifest_sha256: data.manifest_sha256,
                        loaded_at: data.loaded_at,
                        storage: data.storage,
                      }}
                    />
                    <p className="mt-3 text-sm">
                      Sem banco de dados ou importação persistente. Contatos são
                      suprimidos na cópia exibida. Anexos mostram apenas os
                      descritores disponíveis; sem nova transcrição ou leitura
                      de imagens. Rechecagens não substituem o julgamento
                      principal. O detector já fornecia a indicação de
                      encaminhamento ao modelo.
                    </p>
                  </details>
                </div>
              )}
              {tab === "runs" && (
                <div className="space-y-5">
                  <Panel title="Explorar todas as execuções">
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                      <label className="min-w-0 text-xs font-medium sm:col-span-2">
                        Buscar cenário, texto ou ID
                        <input
                          className="mt-1 h-10 w-full rounded-md border bg-background px-3 text-sm focus:ring-2 focus:ring-primary"
                          value={search}
                          onChange={(e) => setSearch(e.target.value)}
                          placeholder="Ex.: R-stock-03 ou azitromicina"
                        />
                      </label>
                      <Filter
                        label="Arquitetura"
                        value={architecture}
                        onChange={setArchitecture}
                        options={Object.entries(labels)}
                      />
                      <Filter
                        label="Resultado da tarefa"
                        value={outcome}
                        onChange={setOutcome}
                        options={["Sucesso", "Falha", "Desconhecido"].map(
                          (x) => [x, x],
                        )}
                      />
                      <Filter
                        label="Estrato"
                        value={stratum}
                        onChange={setStratum}
                        options={[
                          ...new Set(data.rows.map((r) => r.stratum)),
                        ].map((s) => [s, strata[s] ?? s])}
                      />
                      <Filter
                        label="Dificuldade"
                        value={difficulty}
                        onChange={setDifficulty}
                        options={[
                          ...new Set(data.rows.map((r) => r.difficulty)),
                        ].map((d) => [d, difficulties[d] ?? d])}
                      />
                      <Filter
                        label="Julgamento"
                        value={judge}
                        onChange={setJudge}
                        options={[
                          ["valid", "Válido"],
                          ["invalid", "Ausente / inválido"],
                        ]}
                      />
                      <Filter
                        label="Modo de resolução esperado"
                        value={mode}
                        onChange={setMode}
                        options={[
                          ...new Set(
                            data.rows.map((r) => r.expected_resolution_mode),
                          ),
                        ].map((m) => [m, modes[m] ?? m.replaceAll("_", " ")])}
                      />
                    </div>
                    <div className="mt-4 flex flex-wrap items-end justify-between gap-3">
                      <p
                        role="status"
                        data-testid="filtered-count"
                        className="text-sm"
                      >
                        <strong>{filtered.length}</strong> de 600 execuções ·{" "}
                        {filtered.filter((r) => r.task_success === true).length}{" "}
                        sucessos ·{" "}
                        {
                          filtered.filter((r) => r.task_success === false)
                            .length
                        }{" "}
                        falhas
                      </p>
                      <div className="flex flex-wrap items-end gap-2">
                        <Filter
                          label="Ordenar"
                          value={sort}
                          onChange={setSort}
                          all={false}
                          options={[
                            ["order", "Ordem experimental"],
                            ["scenario", "Cenário"],
                            ["latency", "Maior latência"],
                            ["tokens", "Mais tokens"],
                          ]}
                        />
                        <Button variant="outline" onClick={clear}>
                          Limpar filtros
                        </Button>
                        <Button
                          variant="outline"
                          onClick={exportCsv}
                          disabled={!filtered.length}
                        >
                          <Download className="h-4 w-4" />
                          CSV de métricas
                        </Button>
                      </div>
                    </div>
                    <div className="mt-4 overflow-x-auto">
                      <table className="w-full min-w-[720px] text-left text-sm">
                        <caption className="sr-only">
                          Execuções filtradas, 30 registros por página
                        </caption>
                        <thead className="bg-muted">
                          <tr>
                            {[
                              "Cenário",
                              "Arquitetura",
                              "Repetição",
                              "Tarefa",
                              "Latência e2e",
                              "Tokens",
                              "Inspeção",
                            ].map((x) => (
                              <th className="p-3" key={x}>
                                {x}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {filtered
                            .slice(page * 30, (page + 1) * 30)
                            .map((r) => (
                              <tr
                                key={r.run_id}
                                className={`border-t ${selected === r.run_id ? "bg-primary/5" : ""}`}
                              >
                                <th className="p-3 font-medium">
                                  {r.scenario_id}
                                </th>
                                <td className="p-3">
                                  {labels[r.architecture]}
                                </td>
                                <td className="p-3">{r.repetition}</td>
                                <td className="p-3">
                                  <Outcome value={r.task_success} />
                                  {!r.judge_valid && (
                                    <span className="mt-1 block text-xs">
                                      Juiz ausente
                                    </span>
                                  )}
                                </td>
                                <td className="p-3">
                                  {duration(r.end_to_end_latency_ms)}
                                </td>
                                <td className="p-3">{num(r.total_tokens)}</td>
                                <td className="p-3">
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    aria-label={`Abrir ${r.scenario_id} ${labels[r.architecture]} repetição ${r.repetition}`}
                                    onClick={() => selectRun(r.run_id)}
                                  >
                                    Abrir
                                  </Button>
                                </td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                    {!filtered.length && (
                      <p className="py-8 text-center text-sm">
                        Nenhum registro corresponde aos filtros. Use “Limpar
                        filtros” para voltar ao lote completo.
                      </p>
                    )}
                    <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                      <p className="text-xs text-muted-foreground">
                        Repetições originais de 0 a 4. Filtrar não altera os
                        resultados.
                      </p>
                      <div className="flex items-center gap-3">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={page === 0}
                          onClick={() => setPage((p) => p - 1)}
                        >
                          Anterior
                        </Button>
                        <span className="text-sm">
                          Página {page + 1} de{" "}
                          {Math.max(1, Math.ceil(filtered.length / 30))}
                        </span>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={(page + 1) * 30 >= filtered.length}
                          onClick={() => setPage((p) => p + 1)}
                        >
                          Próxima
                        </Button>
                      </div>
                    </div>
                  </Panel>
                  {selected && (
                    <section
                      aria-label="Inspeção da execução"
                      className="space-y-4"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <h2
                          ref={heading}
                          tabIndex={-1}
                          className="text-xl font-semibold outline-none"
                        >
                          {detail
                            ? `${detail.record.scenario_id} · ${labels[detail.record.architecture]} · repetição ${detail.record.repetition}`
                            : "Inspeção da execução"}
                        </h2>
                        <div className="flex flex-wrap gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={index <= 0}
                            onClick={() =>
                              selectRun(filtered[index - 1].run_id)
                            }
                          >
                            Registro anterior
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={index < 0 || index >= filtered.length - 1}
                            onClick={() =>
                              selectRun(filtered[index + 1].run_id)
                            }
                          >
                            Próximo registro
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => selectRun(null)}
                          >
                            Fechar
                          </Button>
                        </div>
                      </div>
                      {detailError ? (
                        <p
                          role="alert"
                          className="rounded-xl border border-destructive p-4"
                        >
                          {detailError}
                        </p>
                      ) : !detail ? (
                        <p role="status">Carregando o registro…</p>
                      ) : (
                        <>
                          <div className="flex flex-wrap gap-2">
                            <Outcome value={detail.record.task_success} />
                            <Badge variant="outline">
                              Técnico: {detail.record.status}
                            </Badge>
                            <Badge variant="outline">
                              Juiz:{" "}
                              {detail.record.judge_valid
                                ? "válido"
                                : "ausente / inválido"}
                            </Badge>
                            <Badge variant="outline">
                              e2e{" "}
                              {duration(detail.record.end_to_end_latency_ms)}
                            </Badge>
                            <Badge variant="outline">
                              {num(detail.record.total_tokens)} tokens
                            </Badge>
                          </div>
                          <nav
                            aria-label="Detalhes da execução"
                            className="flex flex-wrap gap-2"
                          >
                            {[
                              ["conversation", "Conversa e resposta"],
                              ["evaluation", "Gabarito e avaliação"],
                              ["trajectory", "Agentes e ferramentas"],
                              ["events", "Eventos"],
                              ["compare", "Comparar arquiteturas"],
                            ].map(([key, label]) => (
                              <Button
                                size="sm"
                                key={key}
                                variant={
                                  detailTab === key ? "default" : "outline"
                                }
                                aria-current={
                                  detailTab === key ? "page" : undefined
                                }
                                onClick={() => setDetailTab(key)}
                              >
                                {label}
                              </Button>
                            ))}
                          </nav>
                          {detailTab === "conversation" && (
                            <div className="grid items-start gap-5 lg:grid-cols-2">
                              <Panel title="Entrada disponível no momento da execução">
                                <p className="mb-3 text-xs text-muted-foreground">
                                  Prefixo real selecionado; sem mensagens
                                  futuras.
                                </p>
                                <ConversationHistory
                                  value={detail.input.history}
                                />
                                <div className="my-4 rounded-lg border bg-primary/5 p-4">
                                  <MarkdownContent
                                    content={
                                      detail.input.text ?? "Entrada sem texto"
                                    }
                                  />
                                </div>
                                <details>
                                  <summary className="cursor-pointer text-sm font-medium">
                                    Descritores dos anexos
                                  </summary>
                                  <JsonView value={detail.input.attachments} />
                                </details>
                              </Panel>
                              <Panel title="Resposta final coletada">
                                <MarkdownContent
                                  content={
                                    detail.final_text || "Sem resposta final"
                                  }
                                />
                                <p className="mt-5 text-xs text-muted-foreground">
                                  Resposta preservada, com contatos suprimidos
                                  na visualização.
                                </p>
                              </Panel>
                            </div>
                          )}
                          {detailTab === "evaluation" && (
                            <div className="space-y-5">
                              <Panel title="Conteúdo, procedimento e encaminhamento">
                                <div className="grid gap-3 sm:grid-cols-3">
                                  <Metric
                                    label="Conteúdo da tarefa"
                                    value={conformity(
                                      detail.record.content_success,
                                    )}
                                    note="Classificação registrada"
                                  />
                                  <Metric
                                    label="Procedimento obrigatório"
                                    value={
                                      detail.record.procedure_applicable
                                        ? conformity(
                                            detail.record.procedure_compliance,
                                          )
                                        : "Não aplicável"
                                    }
                                    note="Verificador objetivo de evidência"
                                  />
                                  <Metric
                                    label="Modo esperado"
                                    value={
                                      modes[
                                        detail.record.expected_resolution_mode
                                      ] ??
                                      detail.record.expected_resolution_mode.replaceAll(
                                        "_",
                                        " ",
                                      )
                                    }
                                    note="Sucesso conforme o gabarito"
                                  />
                                </div>
                                <JsonView
                                  value={
                                    detail.evaluation
                                      ? Object.fromEntries(
                                          Object.entries(
                                            detail.evaluation,
                                          ).filter(([key]) =>
                                            /referral|transfer/.test(key),
                                          ),
                                        )
                                      : null
                                  }
                                />
                              </Panel>
                              <Panel title="Critérios do juiz principal">
                                {detail.evaluation ? (
                                  <div className="space-y-3">
                                    {detail.evaluation.criteria.map((c, i) => (
                                      <div
                                        key={`${c.criterion_id}-${i}`}
                                        className="rounded-lg border p-4"
                                      >
                                        <p className="flex gap-2 font-medium">
                                          <Badge
                                            variant={
                                              c.met ? "success" : "destructive"
                                            }
                                          >
                                            {c.met ? "Aprovado" : "Reprovado"}
                                          </Badge>
                                          {c.criterion_id}
                                        </p>
                                        <p className="mt-2 text-sm">
                                          {c.reason}
                                        </p>
                                        <details className="mt-2">
                                          <summary className="cursor-pointer text-xs">
                                            Referências de evidência
                                          </summary>
                                          <JsonView value={c.evidence_refs} />
                                        </details>
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <p role="status">
                                    Julgamento inválido preservado como ausente.
                                    Sem notas imputadas. A falha objetiva
                                    permanece registrada.
                                  </p>
                                )}
                              </Panel>
                              <Panel title="Cinco dimensões de qualidade">
                                <div className="grid gap-3 sm:grid-cols-2">
                                  {Object.entries(dimensions).map(
                                    ([key, label]) => (
                                      <div
                                        key={key}
                                        className="rounded-lg border p-4"
                                      >
                                        <h3 className="text-sm font-medium">
                                          {label} ·{" "}
                                          {detail.evaluation?.quality[key] ??
                                            "Ausente"}
                                          {detail.evaluation && " / 5"}
                                        </h3>
                                        <p className="mt-2 text-sm text-muted-foreground">
                                          {detail.evaluation?.quality_reasons[
                                            key
                                          ] ?? "Não avaliada"}
                                        </p>
                                      </div>
                                    ),
                                  )}
                                </div>
                              </Panel>
                              <Panel title="Gabarito e verificador objetivo">
                                <details open>
                                  <summary className="cursor-pointer font-medium">
                                    Gabarito congelado
                                  </summary>
                                  <JsonView value={detail.gold} />
                                </details>
                                <details className="mt-4">
                                  <summary className="cursor-pointer font-medium">
                                    Verificação objetiva completa
                                  </summary>
                                  <JsonView value={detail.objective_checks} />
                                </details>
                              </Panel>
                            </div>
                          )}
                          {detailTab === "trajectory" && (
                            <div className="space-y-5">
                              <Panel title="Trajetória observada">
                                <p className="mb-4 text-sm text-muted-foreground">
                                  Chamadas de agente e delegações na sequência
                                  original; não é encaminhamento a um
                                  profissional.
                                </p>
                                <ol className="space-y-3">
                                  {detail.events
                                    .filter(
                                      (e) =>
                                        (e.eventFamily === "agent" &&
                                          e.eventName === "started") ||
                                        e.eventFamily === "handoff",
                                    )
                                    .map((e) => (
                                      <li
                                        key={e.sequence}
                                        className="rounded-lg border-l-4 border-primary bg-muted p-3"
                                      >
                                        <p className="text-sm font-medium">
                                          #{e.sequence} ·{" "}
                                          {e.actorName ?? "Delegação"} ·{" "}
                                          {e.eventFamily}.{e.eventName}
                                        </p>
                                        <p className="mt-1 text-xs text-muted-foreground">
                                          {e.recorded_at} · {e.status}
                                        </p>
                                        {e.eventFamily === "handoff" && (
                                          <JsonView value={e.payload} />
                                        )}
                                      </li>
                                    ))}
                                </ol>
                              </Panel>
                              <Panel title="Consultas e retornos das ferramentas">
                                <div className="space-y-3">
                                  {detail.events
                                    .filter((e) => e.eventFamily === "tool")
                                    .map((e) => (
                                      <details
                                        key={e.sequence}
                                        className="rounded-lg border p-3"
                                      >
                                        <summary className="cursor-pointer text-sm font-medium">
                                          #{e.sequence} ·{" "}
                                          {e.toolName ?? e.actorName} ·{" "}
                                          {e.eventName} · {e.status}
                                        </summary>
                                        <JsonView value={e.payload} />
                                      </details>
                                    ))}
                                  {!detail.events.some(
                                    (e) => e.eventFamily === "tool",
                                  ) && (
                                    <p className="text-sm">
                                      Nenhuma chamada de ferramenta registrada.
                                    </p>
                                  )}
                                </div>
                              </Panel>
                            </div>
                          )}
                          {detailTab === "events" && (
                            <Panel
                              title={`${detail.events.length} eventos registrados`}
                            >
                              <p className="mb-4 text-sm text-muted-foreground">
                                Ordem da origem. A configuração extensa do
                                experimento foi omitida desta lista; nenhum
                                evento foi recriado.
                              </p>
                              <div className="space-y-2">
                                {detail.events.map((e) => (
                                  <details
                                    key={e.sequence}
                                    className="rounded-lg border p-3"
                                  >
                                    <summary className="cursor-pointer break-words text-sm">
                                      #{e.sequence} · {e.eventFamily}.
                                      {e.eventName} · {e.actorName ?? "runtime"}{" "}
                                      · {e.status}
                                    </summary>
                                    <p className="mt-2 text-xs">
                                      {e.recorded_at}{" "}
                                      {e.durationMs != null &&
                                        `· ${duration(e.durationMs)}`}
                                    </p>
                                    <JsonView value={e.payload} />
                                  </details>
                                ))}
                              </div>
                            </Panel>
                          )}
                          {detailTab === "compare" && (
                            <Panel title="Mesmo cenário e mesma repetição">
                              <p className="mb-4 text-sm text-muted-foreground">
                                Comparação pareada das três condições.{" "}
                                {peers.length === 3
                                  ? new Set(
                                      peers.map((p) => p.initial_input_sha256),
                                    ).size === 1
                                    ? "Hashes da entrada inicial idênticos."
                                    : "Consulte os hashes de cada condição."
                                  : "Carregando as três condições…"}
                              </p>
                              <div className="grid items-start gap-4 xl:grid-cols-3">
                                {archs
                                  .map((a) =>
                                    peers.find(
                                      (p) => p.record.architecture === a,
                                    ),
                                  )
                                  .filter((p): p is ResearchDetail => !!p)
                                  .map((p) => (
                                    <article
                                      className="min-w-0 rounded-lg border p-4"
                                      key={p.record.run_id}
                                    >
                                      <h3 className="mb-3 font-semibold">
                                        {labels[p.record.architecture]}
                                      </h3>
                                      <Outcome value={p.record.task_success} />
                                      <p className="my-3 text-xs text-muted-foreground">
                                        {duration(
                                          p.record.end_to_end_latency_ms,
                                        )}{" "}
                                        · {num(p.record.total_tokens)} tokens ·{" "}
                                        {p.record.model_requests} chamadas
                                      </p>
                                      <MarkdownContent content={p.final_text} />
                                      <Button
                                        className="mt-4"
                                        variant="outline"
                                        size="sm"
                                        onClick={() =>
                                          selectRun(p.record.run_id)
                                        }
                                      >
                                        Inspecionar{" "}
                                        {labels[p.record.architecture]}
                                      </Button>
                                    </article>
                                  ))}
                              </div>
                            </Panel>
                          )}
                          <details className="rounded-xl border bg-card p-4">
                            <summary className="cursor-pointer text-sm">
                              IDs, métricas e hashes de origem
                            </summary>
                            <JsonView
                              value={{
                                record: detail.record as unknown as Json,
                                initial_input_sha256:
                                  detail.initial_input_sha256,
                                source_hashes: detail.source_hashes,
                              }}
                            />
                          </details>
                        </>
                      )}
                    </section>
                  )}
                </div>
              )}
              {tab === "scenarios" && (
                <Panel title="40 cenários · cinco repetições por arquitetura">
                  <p className="mb-4 text-sm text-muted-foreground">
                    Sucessos por cenário e condição. Abra o cenário para
                    examinar as 15 unidades, incluindo falhas.
                  </p>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[600px] text-left text-sm">
                      <thead>
                        <tr>
                          {[
                            "Cenário",
                            "Estrato",
                            "Dificuldade",
                            ...archs.map((a) => labels[a]),
                            "Registros",
                          ].map((x) => (
                            <th key={x} className="p-3">
                              {x}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {[...new Set(data.rows.map((r) => r.scenario_id))]
                          .sort()
                          .map((s) => {
                            const rows = data.rows.filter(
                              (r) => r.scenario_id === s,
                            );
                            return (
                              <tr key={s} className="border-t">
                                <th className="p-3 font-medium">{s}</th>
                                <td className="p-3">
                                  {strata[rows[0].stratum] ?? rows[0].stratum}
                                </td>
                                <td className="p-3">
                                  {difficulties[rows[0].difficulty] ??
                                    rows[0].difficulty}
                                </td>
                                {archs.map((a) => (
                                  <td className="p-3" key={a}>
                                    {
                                      rows.filter(
                                        (r) =>
                                          r.architecture === a &&
                                          r.task_success,
                                      ).length
                                    }{" "}
                                    / 5
                                  </td>
                                ))}
                                <td className="p-3">
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    aria-label={`Explorar ${s}`}
                                    onClick={() => {
                                      clear();
                                      setSearch(s);
                                      selectRun(null);
                                    }}
                                  >
                                    Explorar
                                  </Button>
                                </td>
                              </tr>
                            );
                          })}
                      </tbody>
                    </table>
                  </div>
                </Panel>
              )}
              {tab === "quality" && (
                <div className="space-y-5">
                  <Panel title="Distribuição das notas de qualidade">
                    <p className="mb-4 text-sm text-muted-foreground">
                      599 avaliações válidas. A nota ausente de Workflow não
                      entra nas distribuições. Contagens por dimensão; notas de
                      1 a 5.
                    </p>
                    <div className="grid gap-5 lg:grid-cols-2">
                      {Object.entries(dimensions).map(([key, label]) => (
                        <div className="rounded-lg border p-4" key={key}>
                          <h3 className="mb-4 font-medium">{label}</h3>
                          {archs.map((a) => {
                            const values = data.rows
                              .filter((r) => r.architecture === a && r.quality)
                              .map((r) => r.quality![key]);
                            return (
                              <div className="mb-4" key={a}>
                                <p className="mb-1 text-xs">
                                  {labels[a]} · n={values.length} · mediana{" "}
                                  {median(values)}
                                </p>
                                <div
                                  className="flex h-6 overflow-hidden rounded"
                                  aria-hidden="true"
                                >
                                  {[1, 2, 3, 4, 5].map((score, i) => (
                                    <div
                                      key={score}
                                      className={
                                        [
                                          "bg-red-600",
                                          "bg-orange-500",
                                          "bg-amber-400",
                                          "bg-teal-400",
                                          "bg-teal-700",
                                        ][i]
                                      }
                                      style={{
                                        width: `${(values.filter((v) => v === score).length / values.length) * 100}%`,
                                      }}
                                    />
                                  ))}
                                </div>
                                <p className="mt-1 text-xs text-muted-foreground">
                                  {[1, 2, 3, 4, 5]
                                    .map(
                                      (s) =>
                                        `${s}: ${values.filter((v) => v === s).length}`,
                                    )
                                    .join(" · ")}
                                </p>
                              </div>
                            );
                          })}
                        </div>
                      ))}
                    </div>
                  </Panel>
                  <Panel title="Consumo separado por etapa">
                    <p className="mb-3 text-sm">
                      Geração, julgamento principal e 15 rechecagens são etapas
                      distintas. As chamadas do juiz não entram nos tokens nem
                      na latência dos agentes.
                    </p>
                    <Consumption data={data} />
                  </Panel>
                  <Panel title="Sucesso por modo de resolução esperado">
                    <div className="space-y-3">
                      {[
                        ...new Set(
                          data.rows.map((r) => r.expected_resolution_mode),
                        ),
                      ].map((m) => {
                        const rows = data.rows.filter(
                          (r) => r.expected_resolution_mode === m,
                        );
                        return (
                          <div
                            key={m}
                            className="flex flex-wrap justify-between gap-2 border-b pb-2 text-sm"
                          >
                            <span>{modes[m] ?? m.replaceAll("_", " ")}</span>
                            <span>
                              {rows.filter((r) => r.task_success).length} /{" "}
                              {rows.length} sucessos ·{" "}
                              {new Set(rows.map((r) => r.scenario_id)).size}{" "}
                              cenários
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </Panel>
                </div>
              )}
            </>
          )}
        </div>
        <footer className="mt-8 border-t py-4 text-xs text-muted-foreground">
          MAB · Consulta local dos resultados congelados · nenhum dado da coleta
          é alterado pela interface.
        </footer>
      </div>
    </main>
  );
}
function Panel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="min-w-0 rounded-xl border bg-card p-4 shadow-sm sm:p-5">
      <h2 className="mb-4 text-base font-semibold">{title}</h2>
      {children}
    </section>
  );
}
function Metric({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note: string;
}) {
  return (
    <div className="min-w-0 rounded-xl border bg-card p-4">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-2 break-words text-2xl font-semibold tracking-tight">
        {value}
      </p>
      <p className="mt-2 text-xs leading-5 text-muted-foreground">{note}</p>
    </div>
  );
}
function Outcome({ value }: { value: boolean | null }) {
  return (
    <Badge
      variant={
        value === true ? "success" : value === false ? "destructive" : "outline"
      }
    >
      {result(value)}
    </Badge>
  );
}
function Filter({
  label,
  value,
  onChange,
  options,
  all = true,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[][];
  all?: boolean;
}) {
  return (
    <label className="min-w-0 text-xs font-medium">
      {label}
      <select
        className="mt-1 h-10 w-full min-w-0 rounded-md border bg-background px-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {all && <option value="">Todos</option>}
        {options.map(([v, name]) => (
          <option key={v} value={v}>
            {name}
          </option>
        ))}
      </select>
    </label>
  );
}
function JsonView({ value }: { value: Json | undefined }) {
  return (
    <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-muted p-3 text-xs leading-5">
      {JSON.stringify(value ?? null, null, 2)}
    </pre>
  );
}

function ConversationHistory({ value }: { value: Json }) {
  if (!Array.isArray(value) || !value.length)
    return (
      <p className="text-sm text-muted-foreground">
        Sem histórico anterior neste prefixo.
      </p>
    );
  return (
    <ol className="space-y-3">
      {value.map((item, index) => {
        if (!item || typeof item !== "object" || Array.isArray(item))
          return null;
        return (
          <li key={index} className="rounded-lg border p-3">
            <p className="mb-2 text-xs font-medium text-muted-foreground">
              {item.role === "customer" ? "Cliente" : "Atendimento"} · mensagem
              anterior {index + 1}
            </p>
            <MarkdownContent
              content={
                typeof item.text === "string"
                  ? item.text
                  : "Mensagem sem texto disponível"
              }
            />
          </li>
        );
      })}
    </ol>
  );
}
function Consumption({ data }: { data: ResearchData }) {
  const resources = data.resources as unknown as {
    agents: { input_tokens: number; output_tokens: number };
    judge: Record<
      string,
      { calls: number; input_tokens: number; output_tokens: number }
    >;
  };
  const stages = [
    {
      label: "Geração dos agentes",
      calls: data.rows.reduce((s, r) => s + r.model_requests, 0),
      ...resources.agents,
    },
    { label: "Juiz principal", ...resources.judge.primary },
    { label: "Rechecagem", ...resources.judge.recheck },
  ];
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[540px] text-left text-sm">
        <caption className="sr-only">
          Tokens e chamadas separados por etapa
        </caption>
        <thead>
          <tr>
            {["Etapa", "Chamadas", "Entrada", "Saída", "Total de tokens"].map(
              (h) => (
                <th key={h} className="p-3">
                  {h}
                </th>
              ),
            )}
          </tr>
        </thead>
        <tbody>
          {stages.map((s) => (
            <tr className="border-t" key={s.label}>
              <th className="p-3 font-medium">{s.label}</th>
              <td className="p-3">{num(s.calls)}</td>
              <td className="p-3">{num(s.input_tokens)}</td>
              <td className="p-3">{num(s.output_tokens)}</td>
              <td className="p-3">{num(s.input_tokens + s.output_tokens)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-xs text-muted-foreground">
        Custo monetário não calculado na coleta. Totais de tokens preservados
        por etapa.
      </p>
    </div>
  );
}
