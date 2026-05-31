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
    quantidade: item.count,
    latencia: item.averageRunDurationMs ? Math.round(item.averageRunDurationMs) : 0,
  }));

  return (
    <div className="w-full">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {title}
      </p>
      <ResponsiveContainer height={180} width="100%">
        <BarChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
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
          <YAxis tick={{ fontSize: 11 }} className="fill-muted-foreground" />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid hsl(var(--border))" }}
            formatter={(value, name) => [
              name === "latencia" ? `${value} ms` : value,
              name === "latencia" ? "Latência média" : "Quantidade",
            ]}
          />
          <Bar dataKey="quantidade" radius={[4, 4, 0, 0]}>
            {chartData.map((_, index) => (
              <Cell fill={COLORS[index % COLORS.length]} key={index} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
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
  if (data.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
        Sem dados disponíveis
      </div>
    );
  }

  const chartData = data.map((item) => ({
    name: formatLabel(item.key),
    value: item.count,
  }));

  return (
    <div className="w-full">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {title}
      </p>
      <ResponsiveContainer height={200} width="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={40}
            outerRadius={70}
            paddingAngle={3}
            dataKey="value"
            label={({ name, percent }) => `${name} (${((percent ?? 0) * 100).toFixed(0)}%)`}
            labelLine={false}
          >
            {chartData.map((_, index) => (
              <Cell fill={COLORS[index % COLORS.length]} key={index} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid hsl(var(--border))" }}
          />
        </PieChart>
      </ResponsiveContainer>
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
        <PolarGrid className="stroke-border/40" />
        <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11 }} className="fill-muted-foreground" />
        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
        <Radar name="Centralizada" dataKey="centralized" stroke="#2563eb" strokeWidth={2.5} fill="none" dot={{ r: 2.5 }} />
        <Radar name="Swarm" dataKey="swarm" stroke="#059669" strokeWidth={2.5} fill="none" dot={{ r: 2.5 }} />
        <Radar name="Workflow" dataKey="workflow" stroke="#7c3aed" strokeWidth={2.5} fill="none" dot={{ r: 2.5 }} />
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
    <div className="w-full">
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
          <Bar dataKey="centralizada" fill="#2563eb" radius={[3, 3, 0, 0]} />
          <Bar dataKey="workflow" fill="#7c3aed" radius={[3, 3, 0, 0]} />
          <Bar dataKey="swarm" fill="#059669" radius={[3, 3, 0, 0]} />
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
