"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const COLORS = ["#2563eb", "#7c3aed", "#059669", "#d97706", "#dc2626", "#6366f1"];

interface DistributionItem {
  key: string;
  count: number;
  averageRunDurationMs?: number | null;
}

interface ArchitectureComparisonItem {
  metric: string;
  centralized: number;
  workflow: number;
  swarm: number;
  centralizedRaw?: number;
  workflowRaw?: number;
  swarmRaw?: number;
}

export function DistributionBarChart({
  data,
  title,
}: {
  data: DistributionItem[];
  title: string;
}) {
  if (data.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
        Sem dados disponíveis
      </div>
    );
  }

  const chartData = data.map((item) => ({
    name: formatLabel(item.key),
    key: item.key,
    quantidade: item.count,
  }));

  return (
    <div className="min-w-0 w-full">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {title}
      </p>
      <div aria-hidden="true">
      <ResponsiveContainer height={180} width="100%">
        <BarChart accessibilityLayer={false} data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 11 }}
            className="fill-muted-foreground"
            interval={0}
            angle={-20}
            textAnchor="end"
            height={50}
          />
          <YAxis allowDecimals={false} tick={{ fontSize: 11 }} className="fill-muted-foreground" />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid hsl(var(--border))" }}
            formatter={(value) => [value, "Execuções"]}
          />
          <Bar dataKey="quantidade" radius={[4, 4, 0, 0]} isAnimationActive={false}>
            {chartData.map((item, index) => (
              <Cell fill={distributionColor(item.key, index)} key={item.key} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      </div>
      <ul aria-label="Execuções por arquitetura" className="mt-2 grid gap-1 text-xs" data-testid="architecture-run-counts">
        {chartData.map((item) => <li className="flex justify-between gap-3" key={item.key}><span>{item.name}</span><span className="font-medium tabular-nums">{item.quantidade}</span></li>)}
      </ul>
    </div>
  );
}

export function DistributionPieChart({
  data,
  title,
}: {
  data: DistributionItem[];
  title: string;
}) {
  const chartData = data.filter((item) => item.count > 0).map((item) => ({
    name: formatLabel(item.key),
    key: item.key,
    value: item.count,
  }));
  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="min-w-0 w-full">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</p>
      {chartData.length === 0 ? (
        <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">Nenhuma chamada registrada.</div>
      ) : (
        <>
          <div aria-hidden="true" className="mx-auto h-44 w-full max-w-[240px]">
            <ResponsiveContainer height="100%" width="100%">
              <PieChart accessibilityLayer={false}>
                <Pie data={chartData} cx="50%" cy="50%" innerRadius={46} outerRadius={75} paddingAngle={2} dataKey="value" isAnimationActive={false} rootTabIndex={-1}>
                  {chartData.map((item, index) => <Cell fill={COLORS[index % COLORS.length]} key={item.key} />)}
                </Pie>
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid hsl(var(--border))" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <ul aria-label="Legenda do uso de ferramentas" className="grid min-w-0 gap-2" data-testid="tool-usage-legend">
            {chartData.map((item, index) => (
              <li className="grid min-w-0 grid-cols-[10px_minmax(0,1fr)_auto] items-start gap-2 text-xs" key={item.key}>
                <span aria-hidden="true" className="mt-1 h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                <span className="break-words leading-relaxed">{item.name}</span>
                <span className="whitespace-nowrap tabular-nums text-muted-foreground">{item.value} · {Math.round(item.value / total * 100)}%</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 border-t pt-2 text-xs text-muted-foreground">{total} {total === 1 ? "chamada no total" : "chamadas no total"}</p>
        </>
      )}
    </div>
  );
}

export function ArchitectureLatencyChart({ data, title }: { data: DistributionItem[]; title: string }) {
  const measured = data.filter((item) => item.averageRunDurationMs != null).map((item) => ({
    name: formatLabel(item.key),
    key: item.key,
    seconds: (item.averageRunDurationMs ?? 0) / 1000,
    count: item.count,
  }));
  return (
    <div className="min-w-0 w-full" data-testid="dashboard-latency-chart">
      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</p>
      <p className="mb-2 text-xs text-muted-foreground">Tempo médio, em segundos.</p>
      {measured.length === 0 ? (
        <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">Sem duração registrada.</div>
      ) : (
        <>
          <div aria-hidden="true">
            <ResponsiveContainer height={180} width="100%">
              <BarChart accessibilityLayer={false} data={measured} layout="vertical" margin={{ top: 4, right: 18, left: 0, bottom: 0 }}>
                <CartesianGrid horizontal={false} strokeDasharray="3 3" className="stroke-border/40" />
                <XAxis type="number" domain={[0, "auto"]} tick={{ fontSize: 10 }} tickFormatter={(value: number) => `${value.toLocaleString("pt-BR")} s`} />
                <YAxis type="category" dataKey="name" width={78} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid hsl(var(--border))" }} formatter={(value) => [`${Number(value).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} s`, "Latência média"]} />
                <Bar dataKey="seconds" radius={[0, 4, 4, 0]} isAnimationActive={false}>
                  {measured.map((item, index) => <Cell fill={distributionColor(item.key, index)} key={item.name} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <ul aria-label="Latência média por arquitetura" className="grid gap-1 text-xs">
            {measured.map((item) => <li className="flex flex-wrap justify-between gap-x-3 gap-y-0.5" key={item.name}><span>{item.name}</span><span className="font-medium tabular-nums">{item.seconds.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} s</span></li>)}
          </ul>
        </>
      )}
    </div>
  );
}

function RadarValueTooltip({ payload }: { payload?: { payload?: ArchitectureComparisonItem }[] }) {
  if (!payload || payload.length === 0) return null;
  const row = payload[0]?.payload;
  if (!row) return null;

  const items: { label: string; color: string; value: number }[] = [
    { label: "Centralizada", color: "#2563eb", value: row.centralizedRaw ?? row.centralized },
    { label: "Workflow", color: "#7c3aed", value: row.workflowRaw ?? row.workflow },
    { label: "Swarm", color: "#059669", value: row.swarmRaw ?? row.swarm },
  ];

  return (
    <div className="rounded-lg border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="mb-1 font-medium">{row.metric}</p>
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-2">
          <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} />
          <span className="text-muted-foreground">{item.label}:</span>
          <span className="font-medium">{item.value}</span>
        </div>
      ))}
    </div>
  );
}

export function ArchitectureRadarChart({
  data,
}: {
  data: ArchitectureComparisonItem[];
}) {
  if (data.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
        Sem dados disponíveis
      </div>
    );
  }

  return (
    <ResponsiveContainer height={280} width="100%">
      <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
        <PolarGrid stroke="hsl(var(--border))" strokeOpacity={0.4} />
        <PolarAngleAxis
          dataKey="metric"
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={{ stroke: "hsl(var(--border))", strokeOpacity: 0.4 }}
        />
        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
        <Radar isAnimationActive={false} name="Centralizada" dataKey="centralized" stroke="#2563eb" strokeWidth={2.5} fill="#2563eb" fillOpacity={0.12} dot={{ r: 2.5 }} />
        <Radar isAnimationActive={false} name="Swarm" dataKey="swarm" stroke="#059669" strokeWidth={2.5} fill="#059669" fillOpacity={0.12} dot={{ r: 2.5 }} />
        <Radar isAnimationActive={false} name="Workflow" dataKey="workflow" stroke="#7c3aed" strokeWidth={2.5} fill="#7c3aed" fillOpacity={0.12} dot={{ r: 2.5 }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Tooltip content={<RadarValueTooltip />} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

export function ArchitectureBarComparison({
  data,
  title,
}: {
  data: { name: string; centralizada: number; workflow: number; swarm: number }[];
  title: string;
}) {
  if (data.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
        Sem dados disponíveis
      </div>
    );
  }

  return (
    <div className="min-w-0 w-full">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {title}
      </p>
      <ResponsiveContainer height={220} width="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} className="fill-muted-foreground" />
          <YAxis tick={{ fontSize: 11 }} className="fill-muted-foreground" />
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid hsl(var(--border))" }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar isAnimationActive={false} dataKey="centralizada" fill="#2563eb" radius={[3, 3, 0, 0]} />
          <Bar isAnimationActive={false} dataKey="workflow" fill="#7c3aed" radius={[3, 3, 0, 0]} />
          <Bar isAnimationActive={false} dataKey="swarm" fill="#059669" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function formatLabel(value: string): string {
  const LABEL_MAP: Record<string, string> = {
    centralized_orchestration: "Centralizada",
    structured_workflow: "Workflow",
    decentralized_swarm: "Swarm",
    all_architectures: "Todas",
    unknown: "Não classificado",
    handoff_to_peer: "Handoff",
    faq_lookup: "FAQ",
    stock_lookup: "Estoque",
    attachment_intake: "Anexo",
    multi_modal: "Multimodal",
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WebP",
    "application/pdf": "PDF",
  };
  return LABEL_MAP[value] ?? value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function distributionColor(key: string, index: number): string {
  return ({ centralized_orchestration: COLORS[0], structured_workflow: COLORS[1], decentralized_swarm: COLORS[2] } as Record<string, string>)[key] ?? COLORS[index % COLORS.length];
}
