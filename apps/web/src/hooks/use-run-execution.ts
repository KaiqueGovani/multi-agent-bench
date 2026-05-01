"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  getRunComparisonContext,
  getRunExecution,
} from "@/lib/api/client";
import { openRunExecutionStream } from "@/lib/sse/events";
import type {
  Run,
  RunComparisonContextResponse,
  RunExecutionEvent,
  RunExecutionProjection,
} from "@/lib/types";

type ConnectionStatus = "idle" | "connecting" | "open" | "closed" | "error" | "reconnecting";

export function useRunExecution(runId: string | null) {
  const [run, setRun] = useState<Run | null>(null);
  const [projection, setProjection] = useState<RunExecutionProjection | null>(null);
  const [executionEvents, setExecutionEvents] = useState<RunExecutionEvent[]>([]);
  const [comparisonContext, setComparisonContext] = useState<RunComparisonContextResponse | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const lastSequenceRef = useRef(0);

  useEffect(() => {
    if (!runId) {
      setRun(null);
      setProjection(null);
      setExecutionEvents([]);
      setComparisonContext(null);
      setConnectionStatus("idle");
      return;
    }
    const activeRunId = runId;

    let source: EventSource | null = null;
    let cancelled = false;
    setError(null);

    async function load() {
      try {
        const refreshExecution = async () => {
          const execution = await getRunExecution(activeRunId);
          if (cancelled) {
            return execution;
          }
          setRun(execution.run);
          setProjection(execution.projection ?? null);
          setExecutionEvents(execution.executionEvents);
          lastSequenceRef.current = execution.executionEvents.at(-1)?.sequenceNo ?? lastSequenceRef.current;
          return execution;
        };

        const [execution, comparison] = await Promise.all([
          refreshExecution(),
          getRunComparisonContext(activeRunId),
        ]);
        if (cancelled) {
          return;
        }
        setRun(execution.run);
        setProjection(execution.projection ?? null);
        setExecutionEvents(execution.executionEvents);
        setComparisonContext(comparison);
        lastSequenceRef.current = execution.executionEvents.at(-1)?.sequenceNo ?? 0;

        source = openRunExecutionStream(
          activeRunId,
          (event) => {
            setExecutionEvents((current) => mergeExecutionEvents(current, [event]));
            lastSequenceRef.current = event.sequenceNo;
            if (
              event.eventFamily === "response"
              || event.eventFamily === "review"
              || event.sequenceNo % 2 === 0
            ) {
              void refreshExecution();
            }
          },
          setConnectionStatus,
          { lastSequenceNo: lastSequenceRef.current },
        );
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "Falha ao carregar execução");
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
      source?.close();
      setConnectionStatus("closed");
    };
  }, [runId]);

  const activeEvent = useMemo(
    () => [...executionEvents].reverse().find((event) => event.status === "running"),
    [executionEvents],
  );

  return {
    activeEvent,
    comparisonContext,
    connectionStatus,
    error,
    executionEvents,
    projection,
    run,
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
