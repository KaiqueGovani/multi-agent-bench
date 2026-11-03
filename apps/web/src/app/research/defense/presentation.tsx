"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import styles from "./presentation.module.css";

type Row = { architecture: string; task_successes: number; planned: number; end_to_end_latency_ms_median_of_case_medians: number };
type Data = { generated: number; technical_successes: number; primary_valid: number; task_successes: number; task_failures: number; architectures: Row[] };
const labels = ["Agente único", "Workflow", "Swarm híbrido"];
// Editorial estimates from the supplied thesis, Table 20, p. 77. Not AWS billing.
const costs = [0.00383, 0.01069, 0.01220];
const format = (n: number, digits = 1) => n.toLocaleString("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
const titles = ["Quando vale a pena dividir o trabalho?", "Três sucessos adicionais. Custo 2,79 vezes maior.", "Concluir o processo é só uma parte da tarefa.", "Mesma tarefa cumprida. Percursos diferentes."];

export function DefensePresentation({ data }: { data: Data }) {
  const [slide, setSlide] = useState(0);
  const [presenting, setPresenting] = useState(false);
  const [details, setDetails] = useState(false);
  const title = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    const handle = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLElement && e.target.closest("button, a, input, summary")) return;
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
        e.preventDefault(); setSlide(s => Math.max(0, Math.min(3, s + (e.key === "ArrowRight" ? 1 : -1)))); setDetails(false);
      }
      if (e.key === "Escape") { setPresenting(false); setDetails(false); }
    };
    window.addEventListener("keydown", handle);
    return () => window.removeEventListener("keydown", handle);
  }, []);
  useEffect(() => { title.current?.focus(); }, [slide]);
  const move = (n: number) => { setSlide(n); setDetails(false); };
  return <main className={`${styles.stage} ${presenting ? styles.presenting : ""}`}>
    <header className={styles.header}>
      <Link href="/research">MAB / Pesquisa</Link>
      <span>Coleta histórica · matrix40-v1-final</span>
      <button onClick={() => { setPresenting(v => !v); title.current?.focus(); }}>{presenting ? "Sair da apresentação" : "Apresentar à banca"}</button>
    </header>
    <section className={styles.content} aria-label={`Tela ${slide + 1} de 4`}>
      <p className={styles.eyebrow}>FELIPE MARIANO & KAIQUE GOVANI · FACENS · TCC 2026</p>
      <h1 ref={title} tabIndex={-1}>{titles[slide]}</h1>
      {slide === 0 && <>
        <p className={styles.lead}>Distribuir uma solicitação entre especialistas melhora a resposta o suficiente para justificar o custo de coordenação?</p>
        <div className={styles.matrix}><strong>40 cenários</strong><span>×</span><strong>3 configurações</strong><span>×</span><strong>5 tentativas</strong><span>=</span><strong>{data.generated} execuções</strong></div>
        <div className={styles.columns}>{[
          ["Supervisor", "Ferramentas", "Resposta do supervisor"],
          ["Roteador", "Especialistas em sequência", "Sintetizador"],
          ["Coordenador", "Especialistas ↔ delegações", "Sintetizador"],
        ].map((flow, i) => <article key={labels[i]} className={styles.flow} style={{ borderTopColor: ["#126b68", "#a45316", "#5751a6"][i] }}><h2>{labels[i]}</h2>{flow.map((step, j) => <div key={step}>{j > 0 && <span aria-hidden="true">↓</span>}<p>{step}</p></div>)}</article>)}</div>
        <p className={styles.note}>Uma resposta por tentativa, a partir do mesmo trecho de atendimento. Fluxos sequenciais e fontes controladas.</p>
      </>}
      {slide === 1 && <>
        <p className={styles.lead}>Workflow teve saldo de três sucessos a mais em 200 tentativas.</p>
        <div className={styles.columns}>{[
          { title: "Sucesso da tarefa", max: 100, values: data.architectures.map(r => r.task_successes / r.planned * 100), text: (v: number, i: number) => `${format(v)}% · ${data.architectures[i].task_successes}/200`, ticks: "0% — 100%" },
          { title: "Latência do núcleo", max: 20, values: data.architectures.map(r => r.end_to_end_latency_ms_median_of_case_medians / 1000), text: (v: number) => `${format(v, 3)} s`, ticks: "0 — 20 segundos" },
          { title: "Custo de geração / tentativa", max: .015, values: costs, text: (v: number) => `US$ ${format(v, 5)}`, ticks: "US$ 0 — US$ 0,015" },
        ].map(metric => <article className={styles.chart} key={metric.title}><h2>{metric.title}</h2>{metric.values.map((v, i) => <div className={styles.barRow} key={labels[i]}><div><span>{labels[i]}</span><strong>{metric.text(v, i)}</strong></div><div className={styles.track}><div style={{ width: `${v / metric.max * 100}%`, background: ["#126b68", "#a45316", "#5751a6"][i] }} /></div></div>)}<small>{metric.ticks}</small></article>)}</div>
        <div className={styles.finding}><strong>Diferença de sucesso · workflow − agente único</strong><span>+1,5 p.p. · IC exploratório 95% de −4,5 a +8,0 p.p.</span></div>
        <p className={styles.note}>Neste conjunto, o agente único teve menor tempo e custo. A análise de sucesso não estabeleceu superioridade do workflow.</p>
      </>}
      {slide === 2 && <>
        <div className={styles.stats}>{[[data.technical_successes,"processos concluídos"],[data.task_successes,"sucessos da tarefa"],[data.task_failures,"falhas da tarefa"],[data.primary_valid,"julgamentos válidos"]].map(([v,l]) => <div key={l}><strong>{v}</strong><span>{l}</span></div>)}</div>
        <h2>R-faq-02 · horário de funcionamento</h2>
        <div className={styles.columns}>{[
          ["01 · Requisito", "Informar 08h às 22h, conforme a fonte simulada de FAQ."],
          ["02 · Procedimento", "A consulta obrigatória de horário não foi realizada nas tentativas das três configurações."],
          ["03 · Resultado", "0/5 sucessos por configuração. Na categoria FAQ inteira, foram 5/40 em cada uma."],
        ].map(([h,p]) => <article className={styles.chart} key={h}><h2>{h}</h2><p>{p}</p></article>)}</div>
        <p className={styles.note}>Resumo técnico público do cenário · TCC, Apêndice B, Tabela 30. A consulta e o conteúdo são verificados separadamente.</p>
      </>}
      {slide === 3 && <>
        <p className={styles.lead}>R-stock-03 · as três configurações cumpriram a tarefa nas cinco tentativas.</p>
        <div className={styles.columns}>{[
          ["Supervisor", "1 invocação · 1 papel"],
          ["Roteador → estoque → FAQ → síntese", "4 invocações · 4 papéis"],
          ["Coordenador → especialistas ↔ retornos → síntese", "5 invocações · 4 papéis · 3 delegações concluídas"],
        ].map(([flow,count], i) => <article className={styles.flow} key={flow}><h2>{labels[i]}</h2><p>{flow}</p><strong>{count}</strong><p>5/5 sucessos no cenário</p></article>)}</div>
        <p className={styles.note}>Reconstrução documental da primeira tentativa · TCC, Figuras 11 e 14. Contagens do cenário são distintas das medianas gerais.</p>
        <div className={styles.finding}><strong>O MAB torna a comparação auditável.</strong><span>Resposta, consultas e coordenação ajudam a explicar o resultado.</span></div>
        <p className={styles.note}>Respostas individuais · fontes simuladas · anexos por metadados · avaliação automática sem validação farmacêutica independente.</p>
      </>}
    </section>
    <footer className={styles.footer}>
      <button onClick={() => setDetails(true)}>Ver detalhes e fontes</button>
      <nav aria-label="Telas da apresentação"><button disabled={slide === 0} onClick={() => move(slide - 1)}>← Anterior</button><span aria-live="polite">{slide + 1} / 4</span><button disabled={slide === 3} onClick={() => move(slide + 1)}>Próxima →</button></nav>
      <span>← → navegar · Esc sair</span>
    </footer>
    {details && <div className={styles.overlay} role="dialog" aria-modal="true" aria-label="Detalhes e fontes" onKeyDown={e => { if (e.key === "Escape") { setDetails(false); title.current?.focus(); } if (e.key === "Tab") { const items = e.currentTarget.querySelectorAll<HTMLElement>("button, a[href]"); const first = items[0], last = items[items.length - 1]; if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); } else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); } } }}><div><button autoFocus onClick={() => setDetails(false)}>Fechar detalhes</button><h2>Fontes e alcance</h2><p>Agregados carregados do arquivo versionado research-data/results/matrix40-v1-final/results-summary.json.</p><p>Latência é a mediana das medianas de cinco tentativas por cenário. A medição abrange o núcleo experimental, processos e arquivos. A avaliação usa 40 cenários como unidades pareadas.</p><p>Custos são estimativas editoriais do TCC, Tabela 20, p. 77. Geração total US$ 5,3446, juiz principal US$ 21,6980 e rechecagem US$ 0,5206 (Tabela 19). O custo da avaliação é contabilizado separadamente.</p><p>Intervalo de sucesso e diferença pareada transcritos da Tabela 12, p. 68, na revisão de 31/10. Os casos usam resumos documentais públicos, sem transcrições de clientes.</p><p>A execução sem julgamento semântico válido permaneceu como falha por consulta obrigatória ausente. Coleta completa e cobertura semântica integral são estados diferentes.</p><a href="https://github.com/KaiqueGovani/multi-agent-bench/tree/3fa15c4140fc701edf1967f1217576cebdd106cf/research-data/results/matrix40-v1-final">Consultar artefatos históricos</a></div></div>}
  </main>;
}
