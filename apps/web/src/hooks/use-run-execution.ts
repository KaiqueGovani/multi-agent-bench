"use client";

import { useEffect, useMemo, useState } from "react";

import {
  getRunComparisonContext,
  getRunExecution,
} from "@/lib/api/client";
import { openRunExecutionStream } from "@/lib/sse/events";
import type {
  RunComparisonContextResponse,
  RunExecutionEvent,
  RunExecutionResponse,
} from "@/lib/types";

type ConnectionStatus = "idle" | "connecting" | "open" | "closed" | "error" | "reconnecting";

const PROJECTION_REFRESH_DELAY_MS = 100;

export function useRunExecution(runId: string | null, { loadComparison = true } = {}) {
  const [execution, setExecution] = useState<RunExecutionResponse | null>(null);
  const [streamed, setStreamed] = useState<{ runId: string; events: RunExecutionEvent[] } | null>(null);
  const [comparisonContext, setComparisonContext] = useState<RunComparisonContextResponse | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("idle");
  const [failure, setFailure] = useState<{ runId: string; message: string } | null>(null);

  useEffect(() => {
    setFailure(null);
    setConnectionStatus(runId ? "connecting" : "idle");
    if (!runId) return;

    const activeRunId = runId;
    let source: EventSource | null = null;
    let cancelled = false;
    let timer: number | undefined;
    let refreshing = false;
    let refreshRequested = false;
    let needsReconnectRefresh = false;

    function scheduleRefresh() {
      refreshRequested = true;
      if (!refreshing && timer === undefined) {
        timer = window.setTimeout(() => {
          timer = undefined;
          void refreshExecution();
        }, PROJECTION_REFRESH_DELAY_MS);
      }
    }

    async function refreshExecution(): Promise<RunExecutionResponse | null> {
      refreshRequested = false;
      refreshing = true;
      try {
        const snapshot = await getRunExecution(activeRunId);
        if (!cancelled) {
          setExecution(snapshot);
          setFailure(null);
        }
        return snapshot;
      } catch (caught) {
        if (!cancelled) {
          setFailure({
            runId: activeRunId,
            message: caught instanceof Error ? caught.message : "Falha ao carregar execução",
          });
        }
        return null;
      } finally {
        refreshing = false;
        if (!cancelled && refreshRequested) scheduleRefresh();
      }
    }

    // A failed comparison request must not block the execution or its stream.
    if (loadComparison) {
      void getRunComparisonContext(activeRunId).then((comparison) => {
        if (!cancelled) setComparisonContext(comparison);
      }).catch(() => {});
    }

    void refreshExecution().then((snapshot) => {
      if (cancelled) return;
      needsReconnectRefresh = !snapshot;
      source = openRunExecutionStream(
        activeRunId,
        (event) => {
          if (cancelled || event.runId !== activeRunId) return;
          setStreamed((current) => ({
            runId: activeRunId,
            events: mergeExecutionEvents(current?.runId === activeRunId ? current.events : [], [event]),
          }));
          // The server can re-publish the final event after committing the run status.
          scheduleRefresh();
        },
        (status) => {
          if (cancelled) return;
          setConnectionStatus(status);
          if (status === "reconnecting" || status === "error") needsReconnectRefresh = true;
          if (status === "open" && needsReconnectRefresh) {
            needsReconnectRefresh = false;
            scheduleRefresh();
          }
        },
        { lastSequenceNo: snapshot?.executionEvents.at(-1)?.sequenceNo },
      );
    });

    return () => {
      cancelled = true;
      source?.close();
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [loadComparison, runId]);

  const currentExecution = execution?.run.id === runId ? execution : null;
  const executionEvents = useMemo(() => mergeExecutionEvents(
    currentExecution?.executionEvents ?? [],
    streamed?.runId === runId ? streamed.events : [],
  ), [currentExecution, runId, streamed]);

  const activeActor = currentExecution?.projection?.activeActorName;
  const latestActorEvent = activeActor
    ? executionEvents.findLast((event) => event.actorName === activeActor)
    : executionEvents.at(-1);
  const activeEvent = currentExecution?.run.status === "running" && latestActorEvent?.status === "running"
    ? latestActorEvent
    : undefined;

  return {
    activeEvent,
    comparisonContext: comparisonContext?.run.id === runId ? comparisonContext : null,
    connectionStatus,
    error: failure?.runId === runId ? failure.message : null,
    executionEvents,
    projection: currentExecution?.projection ?? null,
    run: currentExecution?.run ?? null,
  };
}

function mergeExecutionEvents(
  currentEvents: RunExecutionEvent[],
  incomingEvents: RunExecutionEvent[],
): RunExecutionEvent[] {
  const byId = new Map<string, RunExecutionEvent>();
  for (const event of currentEvents) {
    byId.set(event.id, event);
  }
  for (const event of incomingEvents) {
    byId.set(event.id, event);
  }
  return Array.from(byId.values()).sort((left, right) => left.sequenceNo - right.sequenceNo);
}
