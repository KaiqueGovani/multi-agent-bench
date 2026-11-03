import type { Metadata } from "next";
import Link from "next/link";

import { loadComparisonV44, V44_FIGURES } from "@/lib/corrected-comparison/v44-results";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const metadata: Metadata = { title: "Comparação arquitetural v4.4 · MAB" };

const labels = {
  centralized_orchestration: "Supervisor + especialistas",
  structured_workflow: "Workflow estruturado",
  decentralized_swarm: "Swarm com handoffs",
};
const phaseLabels: Record<string, string> = { generation: "Geração", primary: "Julgamento primário", recheck: "Rechecagem" };
const decimal = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "USD", maximumFractionDigits: 4 });
const currencyText = (value: number | null) => value === null ? "N/D" : currency.format(value);
const seconds = (value: number | null) => value === null ? "N/D" : `${decimal.format(value / 1000)} s`;
const artifactUrl = (name: string) => `/research/comparison-v44/files/${encodeURIComponent(name)}`;
const headerCell = "p-3 font-medium";
const cell = "p-3 tabular-nums";
const link = "text-primary underline underline-offset-4";

export default async function ComparisonV44Page() {
  const data = await loadComparisonV44();

  return (
    <main className="mx-auto max-w-7xl space-y-8 p-5 md:p-8" data-testid="comparison-v44">
      <header className="space-y-3 border-b pb-5">
        <nav aria-label="Pesquisa" className="flex flex-wrap gap-4 text-sm">
          <Link href="/" className={link}>Chat da POC</Link>
          <Link href="/research" className={link}>Pesquisa</Link>
          <Link href="/research/comparison-v42" className={link}>Histórico v4.2</Link>
        </nav>
        <h1 className="text-2xl font-semibold tracking-tight">Comparação arquitetural v4.4</h1>
        <p className="max-w-4xl text-sm text-muted-foreground">Supervisor com agentes especialistas como ferramentas, workflow estruturado e swarm com coordenador, handoffs entre especialistas e síntese central, comparados nos mesmos cenários derivados de conversas do WhatsApp.</p>
      </header>

      {data.state === "pending" ? (
        <section role="status" className="rounded-lg border bg-card p-6" data-testid="comparison-v44-pending">
          <h2 className="font-semibold">Resultados consolidados indisponíveis</h2>
          <p className="mt-2 text-sm text-muted-foreground">A página requer o inventário, a proveniência e as 600 combinações do export sanitizado v4.4.</p>
        </section>
      ) : (
        <>
          <section aria-labelledby="results-title" className="space-y-4" data-testid="comparison-v44-ready">
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="rounded-md bg-emerald-700 px-2 py-1 text-white">{data.units} execuções únicas</span>
              <span className="rounded-md border px-2 py-1">{data.scenarios} cenários × {data.repetitions} repetições × 3 arquiteturas</span>
              {data.humanReviewPending && <span className="rounded-md border px-2 py-1">Revisão humana pendente</span>}
            </div>
            <h2 id="results-title" className="text-lg font-semibold">Sucesso da tarefa</h2>
            <p className="max-w-4xl text-sm text-muted-foreground">O desfecho combina conclusão técnica, conformidade arquitetural, conteúdo e comprovação das consultas obrigatórias. O julgamento de conteúdo é automatizado e provisório.</p>
            <div className="grid gap-3 md:grid-cols-3">
              {data.summaries.map((row) => (
                <article className="rounded-lg border bg-card p-4" key={row.architecture}>
                  <h3 className="font-medium">{labels[row.architecture]}</h3>
                  <p className="mt-3 text-3xl font-semibold tabular-nums">{row.task_successes}/{row.planned}</p>
                  <p className="mt-2 text-sm text-muted-foreground">{row.task_failures} falhas · {row.task_unknown} desconhecidas</p>
                </article>
              ))}
            </div>
            <p className="text-sm text-muted-foreground">{data.successes}/{data.units} sucessos no lote e {data.schemaValid}/{data.units} avaliações válidas no esquema.</p>
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full min-w-[640px] text-left text-sm">
                <caption className="sr-only">Denominadores dos resultados v4.4</caption>
                <thead className="bg-muted/50"><tr>{["Arquitetura", "Conclusão técnica", "Contrato", "Conteúdo", "Consulta obrigatória"].map((name) => <th className={headerCell} key={name}>{name}</th>)}</tr></thead>
                <tbody>{data.summaries.map((row) => <tr key={row.architecture} className="border-t">
                  <th scope="row" className={headerCell}>{labels[row.architecture]}</th>
                  <td className={cell}>{row.technical_successes}/{row.planned}</td>
                  <td className={cell}>{row.architectural_compliant}/{row.planned}</td>
                  <td className={cell}>{row.content_successes}/{row.content_evaluable}</td>
                  <td className={cell}>{row.mandatory_evidence_compliant}/{row.mandatory_evidence_applicable}</td>
                </tr>)}</tbody>
              </table>
            </div>
          </section>

          <section aria-labelledby="pairs-title" className="space-y-3">
            <h2 id="pairs-title" className="text-lg font-semibold">Contrastes pareados por cenário</h2>
            {data.pairs.every((pair) => pair.adjustedP >= 0.05) && <p className="text-sm text-muted-foreground">Nenhum contraste atingiu significância ao nível de 5% após o ajuste de Holm.</p>}
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full min-w-[700px] text-left text-sm">
                <caption className="sr-only">Diferenças de sucesso e intervalos marginais de 95% em pontos percentuais</caption>
                <thead className="bg-muted/50"><tr>{["Condição A", "Condição B", "Cenários", "B − A (pp)", "IC 95% marginal (pp)", "p ajustado"].map((name) => <th className={headerCell} key={name}>{name}</th>)}</tr></thead>
                <tbody>{data.pairs.map((row) => <tr key={`${row.architectureA}-${row.architectureB}`} className="border-t">
                  <td className={cell}>{labels[row.architectureA]}</td><td className={cell}>{labels[row.architectureB]}</td>
                  <td className={cell}>{row.scenarios}</td><td className={cell}>{decimal.format(row.difference)}</td>
                  <td className={cell}>{decimal.format(row.low)} a {decimal.format(row.high)}</td>
                  <td className={cell}>{row.adjustedP.toLocaleString("pt-BR", { maximumFractionDigits: 4 })}</td>
                </tr>)}</tbody>
              </table>
            </div>
          </section>

          <section aria-labelledby="resources-title" className="space-y-3">
            <h2 id="resources-title" className="text-lg font-semibold">Tempo e consumo</h2>
            <p className="text-sm text-muted-foreground">Geração em {data.waves} ondas de até {data.generationWorkers} processos e julgamento com até {data.judgeWorkers} processos. As {data.excludedSequentialUnits} tentativas do lote sequencial anterior ficam fora desta análise.</p>
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full min-w-[580px] text-left text-sm">
                <caption className="sr-only">Latências expressas como medianas das medianas por cenário</caption>
                <thead className="bg-muted/50"><tr>{["Arquitetura", "Núcleo", "Coletor", "Geração estimada"].map((name) => <th className={headerCell} key={name}>{name}</th>)}</tr></thead>
                <tbody>{data.summaries.map((row) => <tr key={row.architecture} className="border-t">
                  <th scope="row" className={headerCell}>{labels[row.architecture]}</th>
                  <td className={cell}>{seconds(row.latency_ms_median_of_case_medians)}</td>
                  <td className={cell}>{seconds(row.end_to_end_latency_ms_median_of_case_medians)}</td>
                  <td className={cell}>{currencyText(row.estimated_generation_cost_usd)}</td>
                </tr>)}</tbody>
              </table>
            </div>
            <p className="text-xs text-muted-foreground">As latências são medianas das medianas por cenário sob a carga observada. Os custos em USD são estimados pelo uso de tokens.</p>
            <div className="flex flex-wrap gap-3">{data.resources.map((row) => <div className="rounded-lg border px-4 py-3 text-sm" key={row.phase}>
              <p className="font-medium">{phaseLabels[row.phase]}</p>
              <p className="tabular-nums text-muted-foreground">{row.requests_with_usage}/{row.requests_started} requisições medidas · {currencyText(row.estimated_cost_usd)}</p>
            </div>)}</div>
          </section>

          <section aria-labelledby="figures-title" className="space-y-3">
            <h2 id="figures-title" className="text-lg font-semibold">Gráficos</h2>
            <div className="grid gap-4 lg:grid-cols-2">{V44_FIGURES.filter(([name]) => data.artifacts.includes(`${name}.png`)).map(([name, caption]) => (
              <figure className="rounded-lg border bg-white p-3" key={name}>
                <img src={artifactUrl(`${name}.png`)} alt={caption} loading="lazy" className="h-auto w-full" />
                <figcaption className="mt-2 flex flex-wrap justify-between gap-2 text-sm text-slate-800">
                  <span>{caption}</span>
                  <span className="flex gap-3"><a className="underline" download href={artifactUrl(`${name}.png`)} aria-label={`${caption}, PNG`}>PNG</a>
                    {data.artifacts.includes(`${name}.svg`) && <a className="underline" download href={artifactUrl(`${name}.svg`)} aria-label={`${caption}, SVG`}>SVG</a>}</span>
                </figcaption>
              </figure>
            ))}</div>
          </section>

          <section aria-labelledby="files-title" className="space-y-3 rounded-lg border p-4">
            <h2 id="files-title" className="text-lg font-semibold">Arquivos sanitizados</h2>
            <p className="break-all text-xs text-muted-foreground">SHA-256 do manifesto {data.manifestSha256}</p>
            <ul className="grid gap-2 text-sm md:grid-cols-2 lg:grid-cols-3">{data.artifacts.filter((name) => !/\.(png|svg)$/.test(name)).map((name) => (
              <li key={name}><a href={artifactUrl(name)} download className={link}>{name}</a></li>
            ))}</ul>
          </section>
        </>
      )}
    </main>
  );
}
