import { headers } from "next/headers";

import { ResearchWorkspace } from "@/components/research/research-workspace";
import { canAccessPrivateReplay } from "@/lib/research/server";

export default async function ResearchPage() {
  const showReplay = canAccessPrivateReplay(await headers());
  const comparisons = (
    <nav aria-label="Comparações publicadas" className="flex flex-wrap gap-4 text-sm">
      <a href="/research/defense" className="font-medium text-primary underline underline-offset-4">Apresentar à banca · coleta histórica</a>
      <a href="/research/comparison-v44" className="font-medium text-primary underline underline-offset-4">Resultados v4.4</a>
      <a href="/research/comparison-v42" className="text-primary underline underline-offset-4">Histórico v4.2</a>
    </nav>
  );

  if (!showReplay) {
    return (
      <main className="mx-auto max-w-7xl space-y-4 p-5 md:p-8">
        <a href="/" className="text-sm text-primary underline underline-offset-4">Chat da POC</a>
        <h1 className="text-2xl font-semibold tracking-tight">Pesquisa</h1>
        <p className="text-sm text-muted-foreground">Comparações arquiteturais, métricas e gráficos dos lotes publicados.</p>
        {comparisons}
      </main>
    );
  }

  return (
    <>
      <div className="border-b bg-card"><div className="mx-auto max-w-7xl px-4 py-3">{comparisons}</div></div>
      <ResearchWorkspace />
    </>
  );
}
