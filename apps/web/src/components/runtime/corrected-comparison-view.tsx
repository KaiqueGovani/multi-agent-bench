import React from "react";
import type { ComparisonArchitecture, CorrectedComparisonData } from "@/lib/corrected-comparison/results";

const labels: Record<ComparisonArchitecture, string> = {
  centralized_orchestration: "Supervisor + especialistas",
  structured_workflow: "Workflow estruturado",
  decentralized_swarm: "Swarm descentralizado",
};
const colors = ["border-blue-600", "border-amber-600", "border-emerald-600"];
const phaseLabels: Record<string, string> = { generation: "Geração principal", judgment: "Julgamento principal", recheck: "Rechecagem do juiz", engineering_pilot: "Piloto de engenharia", engineering_pilot_judgment: "Julgamento do piloto", api_integration: "Integração pela API" };
const usd = (value: number | null) => value === null ? "N/D" : new Intl.NumberFormat("pt-BR", { style: "currency", currency: "USD", maximumFractionDigits: 4 }).format(value);
const ms = (value: number | null) => value === null ? "N/D" : `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(value)} ms`;
const fraction = (value: number, denominator: number) => `${value}/${denominator}`;
const artifactUrl = (name: string) => `/research/comparison-v42/files/${encodeURIComponent(name)}`;

export function CorrectedComparisonView({ data }: { data: CorrectedComparisonData }) {
  return (
    <main className="mx-auto max-w-7xl space-y-6 p-5 md:p-8" data-testid="corrected-comparison">
      <header className="space-y-3 border-b pb-5">
        <a className="text-sm text-primary underline underline-offset-4" href="/">Voltar ao atendimento</a>
        <h1 className="text-2xl font-semibold tracking-tight">Comparação arquitetural corrigida · v4.2</h1>
        <p className="max-w-4xl text-sm text-muted-foreground">A condição centralizada usa um supervisor que consulta agentes especialistas como ferramentas e produz a resposta final. Workflow e swarm compõem o mesmo lote novo.</p>
      </header>

      {data.state === "pending" ? (
        <section className="rounded-lg border bg-card p-6" role="status" data-testid="corrected-results-pending">
          <h2 className="font-semibold">Resultados consolidados ainda não disponíveis</h2>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">Os valores serão exibidos após a exportação completa, com inventário, proveniência e todas as combinações planejadas verificadas. Esta página não apresenta resultados parciais nem acessa mensagens ou trajetórias privadas.</p>
          <p className="mt-2 text-sm text-muted-foreground">A centralizada histórica corresponde a um agente único com ferramentas de domínio. Seus números permanecem separados dos resultados corrigidos.</p>
          <a className="mt-4 inline-block text-sm text-primary underline" href="/research/comparison-v42">Atualizar a página</a>
        </section>
      ) : (
        <>
          <div className="flex flex-wrap gap-2 text-xs" data-testid="corrected-results-ready">
            <span className="rounded-md bg-emerald-700 px-2 py-1 text-white">600 unidades únicas verificadas</span>
            <span className="rounded-md border px-2 py-1">40 cenários × 5 repetições × 3 arquiteturas</span>
            <span className="rounded-md border px-2 py-1">{data.protocol}</span>
          </div>

          <section aria-labelledby="new-results-title" className="space-y-4">
            <h2 id="new-results-title" className="text-lg font-semibold">Novo lote completo</h2>
            <div className="grid gap-3 md:grid-cols-3">
              {data.summaries.map((row, index) => (
                <article key={row.architecture} className={`rounded-lg border border-t-4 bg-card p-4 ${colors[index]}`}>
                  <h3 className="font-medium">{labels[row.architecture]}</h3>
                  <p className="mt-3 text-3xl font-semibold">{fraction(row.task_successes, row.planned)}</p>
                  <p className="text-xs text-muted-foreground">sucessos da tarefa / unidades planejadas</p>
                  <p className="mt-3 text-xs text-muted-foreground">Falhas: {row.task_failures} · desconhecidos: {row.task_unknown}</p>
                </article>
              ))}
            </div>
            <p className="text-sm text-muted-foreground">O sucesso exige conclusão técnica, conformidade arquitetural, conteúdo sob o instrumento congelado e consulta obrigatória comprovada. Desconhecidos permanecem explícitos no denominador planejado.</p>
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full min-w-[1080px] text-left text-sm">
                <caption className="sr-only">Denominadores do novo lote por arquitetura</caption>
                <thead className="bg-muted/50"><tr>{["Arquitetura", "Técnico", "Contrato", "Conteúdo", "Fonte obrigatória", "Juízo válido", "Inválido/ausente", "Tarefa desconhecida"].map((heading) => <th className="p-3 font-medium" key={heading}>{heading}</th>)}</tr></thead>
                <tbody>{data.summaries.map((row) => <tr key={row.architecture} className="border-t">
                  <th className="p-3 font-medium">{labels[row.architecture]}</th>
                  <td className="p-3">{fraction(row.technical_successes, row.planned)}</td>
                  <td className="p-3">{fraction(row.architectural_compliant, row.planned)}<small className="block text-muted-foreground">violações {row.architectural_violations}; N/D {row.architectural_unknown}</small></td>
                  <td className="p-3">{fraction(row.content_successes, row.content_evaluable)}<small className="block text-muted-foreground">avaliáveis / {row.planned}: {row.content_evaluable}</small></td>
                  <td className="p-3">{fraction(row.mandatory_evidence_compliant, row.mandatory_evidence_applicable)}<small className="block text-muted-foreground">avaliáveis: {row.mandatory_evidence_evaluable}</small></td>
                  <td className="p-3">{fraction(row.judge_valid_assessment, row.planned)}<small className="block text-muted-foreground">esquema válido: {row.judge_schema_valid}; inconsistentes: {row.judge_internally_inconsistent}</small></td>
                  <td className="p-3">{fraction(row.judge_invalid_or_missing, row.planned)}</td>
                  <td className="p-3">{fraction(row.task_unknown, row.planned)}</td>
                </tr>)}</tbody>
              </table>
            </div>
          </section>

          <section aria-labelledby="resources-title" className="space-y-4">
            <h2 id="resources-title" className="text-lg font-semibold">Tempo e consumo medidos</h2>
            <p className="text-sm text-muted-foreground">Latências abaixo são medianas das medianas por cenário. Núcleo e coletor têm fronteiras distintas; não representam latência de produção pela API ou interface. Custos em {data.pricing.currency} são estimativas de tokens, sem representar cobrança efetiva. Região {data.pricing.region}; tarifa verificada em {data.pricing.checkedOn}.</p>
            <div className="grid gap-3 md:grid-cols-3">{data.summaries.map((row, index) => <article key={row.architecture} className={`space-y-3 rounded-lg border border-t-4 bg-card p-4 ${colors[index]}`}>
              <h3 className="font-medium">{labels[row.architecture]}</h3>
              <dl className="grid grid-cols-2 gap-2 text-sm">
                <dt className="text-muted-foreground">Núcleo</dt><dd className="text-right">{ms(row.latency_ms_median_of_case_medians)}</dd>
                <dt className="text-muted-foreground">Coletor</dt><dd className="text-right">{ms(row.end_to_end_latency_ms_median_of_case_medians)}</dd>
                <dt className="text-muted-foreground">Geração estimada</dt><dd className="text-right">{usd(row.estimated_generation_cost_usd)}</dd>
                <dt className="text-muted-foreground">Por sucesso observado</dt><dd className="text-right">{usd(row.estimated_cost_per_observed_task_success_usd)}</dd>
              </dl>
            </article>)}</div>
            <div className="overflow-x-auto rounded-lg border"><table className="w-full min-w-[620px] text-left text-sm">
              <caption className="sr-only">Consumo separado por fase</caption>
              <thead className="bg-muted/50"><tr>{["Fase", "Requisições com uso / iniciadas", "Custo estimado", "Parcela conhecida"].map((heading) => <th className="p-3 font-medium" key={heading}>{heading}</th>)}</tr></thead>
              <tbody>{data.resources.map((row) => <tr key={row.phase} className="border-t"><th className="p-3 font-medium">{phaseLabels[row.phase] ?? row.phase}</th><td className="p-3">{fraction(row.requests_with_usage, row.requests_started)}</td><td className="p-3">{usd(row.estimated_cost_usd)}</td><td className="p-3">{usd(row.known_partial_estimated_cost_usd)}</td></tr>)}</tbody>
            </table></div>
            <p className="text-xs text-muted-foreground">N/D indica consumo desconhecido. Uma parcela conhecida não substitui um custo total desconhecido. Detalhes de conectividade e tarifas constam no arquivo de consumo.</p>
          </section>

          <section aria-labelledby="figures-title" className="space-y-4">
            <h2 id="figures-title" className="text-lg font-semibold">Gráficos exportáveis</h2>
            <div className="grid gap-4 lg:grid-cols-2">{[["01_sucesso", "Sucesso observado"], ["02_latencia_custo_sucesso", "Latência do coletor, custo e sucesso"], ["03_categorias", "Resultados por categoria"], ["04_consistencia", "Consistência nas cinco tentativas"], ["05_falhas", "Classes exclusivas de falha"]].map(([name, label]) => <figure key={name} className="rounded-lg border bg-white p-3">
              <img alt={label} className="h-auto w-full" loading="lazy" src={artifactUrl(name + ".png")} />
              <figcaption className="mt-2 flex flex-wrap items-center justify-between gap-2 text-sm text-slate-800"><span>{label}</span><span className="flex gap-3"><a download href={artifactUrl(name + ".svg")} className="underline">SVG</a><a download href={artifactUrl(name + ".png")} className="underline">PNG</a></span></figcaption>
            </figure>)}</div>
          </section>

          <section aria-labelledby="historical-title" className="space-y-3 rounded-lg border bg-card p-4">
            <h2 id="historical-title" className="text-lg font-semibold">Histórico separado · v4.1</h2>
            <p className="text-sm text-muted-foreground">A antiga centralizada mede um agente único com ferramentas de domínio. O lote antigo permanece separado; suas respostas não completam a nova coleta. Esta comparação histórica não atribui efeito causal à correção.</p>
            {data.historical.length ? <div className="overflow-x-auto"><table className="w-full min-w-[450px] text-left text-sm"><thead><tr><th className="py-2">Condição histórica</th><th>Sucessos / planejadas</th><th>Desconhecidos</th></tr></thead><tbody>{data.historical.map((row) => <tr key={row.architecture} className="border-t"><th className="py-3 pr-3 font-medium">{row.architecture === "centralized_orchestration" ? "Centralizada histórica · agente único" : labels[row.architecture]}</th><td>{fraction(row.task_successes, row.planned)}</td><td>{row.task_unknown}</td></tr>)}</tbody></table></div> : <p className="text-sm text-muted-foreground">Resumo histórico indisponível.</p>}
          </section>

          <section aria-labelledby="files-title" className="space-y-3 rounded-lg border p-4">
            <h2 id="files-title" className="text-lg font-semibold">Dados quantitativos e proveniência</h2>
            <p className="break-all text-xs text-muted-foreground">Experimento: {data.experimentId} · commit: {data.commit} · SHA-256 do manifesto: {data.manifestSha256}</p>
            <ul className="grid gap-2 text-sm md:grid-cols-2 lg:grid-cols-3">{data.artifacts.filter((name) => !name.endsWith(".png") && !name.endsWith(".svg")).map((name) => <li key={name}><a className="text-primary underline underline-offset-4" download href={artifactUrl(name)}>{name}</a></li>)}</ul>
            <p className="text-xs text-muted-foreground">Somente arquivos quantitativos sanitizados e figuras constam nesta página. A amostra intencional conhecida e as fontes controladas limitam a generalização. Não houve avaliação humana ou farmacêutica, nem validação clínica. A rechecagem usa o mesmo juiz automatizado.</p>
          </section>
        </>
      )}
    </main>
  );
}
