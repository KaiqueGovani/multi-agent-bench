import type { ProcessingEvent } from "@/lib/types";

interface EventTimelineProps {
  events: ProcessingEvent[];
  connectionStatus: string;
}

const statusStyles: Record<string, string> = {
  completed: "border-success bg-green-50 text-success",
  running: "border-action bg-cyan-50 text-action",
  failed: "border-danger bg-red-50 text-danger",
  human_review_required: "border-warning bg-amber-50 text-warning",
  pending: "border-line bg-surface text-muted",
  waiting: "border-warning bg-amber-50 text-warning"
};

export function EventTimeline({ events, connectionStatus }: EventTimelineProps) {
  return (
    <aside className="flex min-h-[320px] flex-col border-t border-line bg-panel lg:min-h-0 lg:border-l lg:border-t-0">
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-ink">Eventos</h2>
          <p className="text-xs text-muted">Timeline operacional</p>
        </div>
        <span className="rounded border border-line px-2 py-1 text-xs text-muted">
          {connectionStatus}
        </span>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {events.length === 0 ? (
          <p className="px-1 py-2 text-sm text-muted">Nenhum evento ainda.</p>
        ) : (
          <ol className="space-y-2">
            {events.map((event) => (
              <li key={event.id} className="border-b border-line pb-2 last:border-b-0">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-ink">{event.eventType}</p>
                    {event.actorName ? (
                      <p className="text-xs text-muted">{event.actorName}</p>
                    ) : null}
                  </div>
                  <span
                    className={`shrink-0 rounded border px-2 py-1 text-xs ${
                      statusStyles[event.status] ?? "border-line bg-surface text-muted"
                    }`}
                  >
                    {event.status}
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted">
                  {new Date(event.createdAt).toLocaleTimeString("pt-BR")}
                  {typeof event.durationMs === "number" ? ` · ${event.durationMs} ms` : ""}
                </p>
              </li>
            ))}
          </ol>
        )}
      </div>
    </aside>
  );
}
