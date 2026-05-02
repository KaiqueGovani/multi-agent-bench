"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  createConversation,
  getConversation,
  getConversationEvents,
  getRunExecution,
  listConversations,
  listOpenReviewTasks,
  resolveReviewTask as resolveReviewTaskRequest,
  sendMessage as sendMultipartMessage
} from "@/lib/api/client";
import { openConversationEventStream } from "@/lib/sse/events";
import type {
  ArchitectureMode,
  Attachment,
  Conversation,
  ConversationSummary,
  ExecutionMode,
  Message,
  ProcessingEvent,
  ReviewTask,
  ReviewTaskStatus,
  Run,
  RunExecutionResponse
} from "@/lib/types";

type ConnectionStatus = "idle" | "connecting" | "open" | "closed" | "error" | "reconnecting";

export function useConversation(architectureMode: ArchitectureMode, executionMode: ExecutionMode = "mock") {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [events, setEvents] = useState<ProcessingEvent[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [reviewTasks, setReviewTasks] = useState<ReviewTask[]>([]);
  const [openReviewTasks, setOpenReviewTasks] = useState<ReviewTask[]>([]);
  const [conversationSummaries, setConversationSummaries] = useState<ConversationSummary[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("idle");
  const [isCreatingConversation, setIsCreatingConversation] = useState(false);
  const [isLoadingConversation, setIsLoadingConversation] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeConversationIdRef = useRef<string | null>(null);
  const lastEventIdRef = useRef<string | null>(null);

  /** Tracks when the last refreshConversationDetail was triggered, for debouncing. */
  const lastRefreshTsRef = useRef(0);

  /** Tracks streaming message runIds with creation timestamps for timeout cleanup. */
  const streamingTimestampsRef = useRef(new Map<string, number>());

  /** Live run execution state for the visual flow panel. */
  const [runExecution, setRunExecution] = useState<RunExecutionResponse | null>(null);
  const runExecLastFetchRef = useRef(0);
  const runExecPendingRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refreshConversations = useCallback(async () => {
    try {
      const response = await listConversations();
      setConversationSummaries(response.conversations);
      return response.conversations;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Falha ao atualizar conversas");
      return [];
    }
  }, []);

  /** Throttled fetch for run execution projection (at most once per 1500ms, with trailing). */
  const fetchRunExecution = useCallback((runId: string) => {
    const THROTTLE_MS = 1500;
    const now = Date.now();
    if (now - runExecLastFetchRef.current < THROTTLE_MS) {
      if (runExecPendingRef.current) clearTimeout(runExecPendingRef.current);
      runExecPendingRef.current = setTimeout(() => fetchRunExecution(runId), THROTTLE_MS);
      return;
    }
    runExecLastFetchRef.current = now;
    getRunExecution(runId)
      .then((res) => setRunExecution(res))
      .catch((err) => console.debug("[flow] projection fetch failed", err));
  }, []);

  const activeArchitectureMode = useMemo<ArchitectureMode>(() => {
    const rawValue = conversation?.metadata.architectureMode;
    return isArchitectureMode(rawValue) ? rawValue : architectureMode;
  }, [architectureMode, conversation?.metadata.architectureMode]);

  const refreshOpenReviewTasks = useCallback(async () => {
    try {
      const response = await listOpenReviewTasks();
      setOpenReviewTasks(response.reviewTasks);
      return response.reviewTasks;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Falha ao atualizar revisões");
      return [];
    }
  }, []);

  const loadConversation = useCallback(async (id: string) => {
    setError(null);
    setIsLoadingConversation(true);
    activeConversationIdRef.current = id;
    setConversationId(id);
    setConversation(null);
    setMessages([]);
    setAttachments([]);
    setEvents([]);
    setRuns([]);
    setReviewTasks([]);
    setRunExecution(null);
    lastEventIdRef.current = null;

    try {
      const detail = await getConversation(id);
      if (activeConversationIdRef.current !== id) {
        return;
      }
      setConversation(detail.conversation);
      setMessages(detail.messages);
      setAttachments(detail.attachments);
      setEvents(detail.events);
      setRuns(detail.runs);
      setReviewTasks(detail.reviewTasks);
      lastEventIdRef.current = getLastEventId(detail.events);
    } catch (caught) {
      if (activeConversationIdRef.current === id) {
        setError(caught instanceof Error ? caught.message : "Falha ao carregar conversa");
      }
    } finally {
      if (activeConversationIdRef.current === id) {
        setIsLoadingConversation(false);
      }
    }
  }, []);

  const refreshConversationDetail = useCallback(async (id: string) => {
    try {
      const detail = await getConversation(id);
      if (activeConversationIdRef.current !== id) {
        return null;
      }
      setConversation(detail.conversation);
      // Replace messages but strip any remaining optimistic/streaming messages
      setMessages((current) => {
        const realMessages = detail.messages;
        // Keep streaming messages that don't yet have a server counterpart
        const activeStreaming = current.filter(
          (m) => m.id.startsWith("streaming-")
        );
        return [...realMessages, ...activeStreaming];
      });
      setAttachments(detail.attachments);
      setEvents((current) => mergeEventsForConversation(id, current, detail.events));
      setRuns(detail.runs);
      setReviewTasks(detail.reviewTasks);
      lastEventIdRef.current = getLastEventId(detail.events) ?? lastEventIdRef.current;
      void refreshConversations();
      void refreshOpenReviewTasks();
      return detail;
    } catch (caught) {
      if (activeConversationIdRef.current === id) {
        setError(caught instanceof Error ? caught.message : "Falha ao atualizar conversa");
      }
      return null;
    }
  }, [refreshConversations]);

  /** Debounced refresh: skips if another refresh happened within 500ms. */
  const debouncedRefreshDetail = useCallback(
    (id: string) => {
      const now = Date.now();
      if (now - lastRefreshTsRef.current < 500) {
        console.debug("[streaming] debounced refresh skipped, recent refresh at", lastRefreshTsRef.current);
        return;
      }
      lastRefreshTsRef.current = now;
      void refreshConversationDetail(id);
    },
    [refreshConversationDetail]
  );

  const refreshEvents = useCallback(async (id: string) => {
    try {
      const response = await getConversationEvents(id);
      if (activeConversationIdRef.current !== id) {
        return [];
      }
      setEvents((current) => mergeEventsForConversation(id, current, response));
      lastEventIdRef.current = getLastEventId(response) ?? lastEventIdRef.current;
      return response;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Falha ao atualizar eventos");
      return [];
    }
  }, []);

  const startConversation = useCallback(async () => {
    setError(null);
    activeConversationIdRef.current = null;
    lastEventIdRef.current = null;
    setConversationId(null);
    setConversation(null);
    setMessages([]);
    setAttachments([]);
    setEvents([]);
    setRuns([]);
    setReviewTasks([]);
    setRunExecution(null);
    setConnectionStatus("idle");
  }, []);

  const selectConversation = useCallback(
    async (id: string) => {
      await loadConversation(id);
      await refreshConversations();
    },
    [loadConversation, refreshConversations]
  );

  const updateReviewTask = useCallback(
    async (
      reviewTaskId: string,
      status: Extract<ReviewTaskStatus, "resolved" | "cancelled" | "in_review">,
      note?: string
    ) => {
      setError(null);
      await resolveReviewTaskRequest(reviewTaskId, {
        note: note?.trim() || undefined,
        resolvedBy: "local_human_reviewer",
        status
      });
      await refreshOpenReviewTasks();
      await refreshConversations();
      if (conversationId) {
        await refreshConversationDetail(conversationId);
      }
    },
    [conversationId, refreshConversationDetail, refreshConversations, refreshOpenReviewTasks]
  );

  const sendMessage = useCallback(
    async (text: string, files: File[]) => {
      if (!text.trim() && files.length === 0) {
        return;
      }
      setIsSending(true);
      setError(null);

      // Build optimistic user message
      const optimisticId = "optimistic-" + crypto.randomUUID();
      const optimisticMsg: Message = {
        id: optimisticId,
        conversationId: conversationId ?? "",
        direction: "inbound",
        contentText: text.trim() || null,
        createdAtClient: new Date().toISOString(),
        createdAtServer: new Date().toISOString(),
        status: "processing",
        correlationId: "",
        metadata: {}
      };

      try {
        let targetConversationId = conversationId;
        if (!targetConversationId) {
          setIsCreatingConversation(true);
          const created = await createConversation(architectureMode);
          targetConversationId = created.conversationId;
          activeConversationIdRef.current = targetConversationId;
          setConversationId(targetConversationId);
          setIsCreatingConversation(false);
          // Update optimistic msg conversationId
          optimisticMsg.conversationId = targetConversationId;
        }

        // Insert optimistic message BEFORE the POST
        setMessages((prev) => [...prev, optimisticMsg]);

        await sendMultipartMessage(targetConversationId, text.trim(), files, activeArchitectureMode, executionMode);
        await refreshConversationDetail(targetConversationId);
        window.setTimeout(() => {
          void refreshConversationDetail(targetConversationId);
          void refreshConversations();
        }, 1600);
      } catch (caught) {
        // Remove optimistic message on error
        setMessages((prev) => prev.filter((m) => m.id !== optimisticId));
        setError(caught instanceof Error ? caught.message : "Falha ao enviar mensagem");
      } finally {
        setIsCreatingConversation(false);
        setIsSending(false);
      }
    },
    [
      activeArchitectureMode,
      architectureMode,
      conversationId,
      executionMode,
      refreshConversationDetail,
      refreshConversations
    ]
  );

  useEffect(() => {
    void refreshConversations();
    void refreshOpenReviewTasks();
  }, [refreshConversations, refreshOpenReviewTasks]);

  // Streaming message timeout cleanup: every 10s, drop streaming messages older than 60s
  useEffect(() => {
    const interval = window.setInterval(() => {
      const now = Date.now();
      const staleRunIds: string[] = [];
      for (const [runId, ts] of streamingTimestampsRef.current.entries()) {
        if (now - ts > 60_000) {
          staleRunIds.push(runId);
        }
      }
      if (staleRunIds.length > 0) {
        console.debug("[streaming] cleaning up stale streaming messages:", staleRunIds);
        for (const runId of staleRunIds) {
          streamingTimestampsRef.current.delete(runId);
        }
        setMessages((prev) => prev.filter((m) => {
          if (!m.id.startsWith("streaming-")) return true;
          const msgRunId = m.id.slice("streaming-".length);
          return !staleRunIds.includes(msgRunId);
        }));
        if (activeConversationIdRef.current) {
          void refreshConversationDetail(activeConversationIdRef.current);
        }
      }
    }, 10_000);
    return () => window.clearInterval(interval);
  }, [refreshConversationDetail]);

  useEffect(() => {
    if (!conversationId) {
      setConnectionStatus("idle");
      return;
    }

    let source: EventSource | null = null;
    let isCancelled = false;

    void refreshEvents(conversationId).then((backlogEvents) => {
      if (isCancelled) {
        return;
      }
      source = openConversationEventStream(
        conversationId,
        (event) => {
          if (activeConversationIdRef.current !== conversationId) {
            return;
          }
          if (event.conversationId !== conversationId) {
            return;
          }
          lastEventIdRef.current = event.id;
          setEvents((current) => {
            return mergeEventsForConversation(conversationId, current, [event]);
          });

          // --- Streaming assistant message handling ---
          const payloadRunId = typeof event.payload?.runId === "string" ? event.payload.runId : null;

          // --- Live projection fetch (throttled) ---
          if (payloadRunId) {
            fetchRunExecution(payloadRunId);
          }

          if (
            event.eventType === "response.partial"
            && typeof event.payload?.contentText === "string"
            && payloadRunId
          ) {
            const streamingId = "streaming-" + payloadRunId;
            const contentText = event.payload.contentText as string;
            streamingTimestampsRef.current.set(payloadRunId, Date.now());
            setMessages((prev) => {
              const existing = prev.findIndex((m) => m.id === streamingId);
              if (existing >= 0) {
                // Replace contentText in-place
                const updated = [...prev];
                updated[existing] = { ...updated[existing], contentText };
                return updated;
              }
              // Append new streaming message
              const streamingMsg: Message = {
                id: streamingId,
                conversationId,
                direction: "outbound",
                contentText,
                createdAtClient: null,
                createdAtServer: event.createdAt,
                status: "processing",
                correlationId: event.correlationId,
                metadata: {}
              };
              return [...prev, streamingMsg];
            });
          }

          if (
            (event.eventType === "response.final" || event.eventType === "processing.completed")
            && payloadRunId
          ) {
            const streamingId = "streaming-" + payloadRunId;
            streamingTimestampsRef.current.delete(payloadRunId);
            setMessages((prev) => prev.filter((m) => m.id !== streamingId));
            debouncedRefreshDetail(conversationId);
          } else if (event.eventType === "response.final" || event.eventType === "processing.completed") {
            // Fallback: no runId in payload — still refresh (backward compat with mock mode)
            debouncedRefreshDetail(conversationId);
          }
        },
        (status) => {
          setConnectionStatus(status);
          if (status === "open") {
            void refreshEvents(conversationId);
          }
          // On SSE error/reconnect: purge ghost streaming messages
          if (status === "error" || status === "reconnecting") {
            console.debug("[streaming] SSE disconnect, purging streaming messages");
            streamingTimestampsRef.current.clear();
            setMessages((prev) => prev.filter((m) => !m.id.startsWith("streaming-")));
            void refreshConversationDetail(conversationId);
          }
        },
        {
          lastEventId: getLastEventId(backlogEvents) ?? lastEventIdRef.current
        }
      );
    });

    return () => {
      isCancelled = true;
      setConnectionStatus("closed");
      source?.close();
      // Clear any pending trailing projection fetch to avoid post-unmount state updates.
      if (runExecPendingRef.current) {
        clearTimeout(runExecPendingRef.current);
        runExecPendingRef.current = null;
      }
    };
  }, [conversationId, debouncedRefreshDetail, fetchRunExecution, refreshConversationDetail, refreshEvents]);

  // Fetch run execution projection when runs change (initial load / new run)
  useEffect(() => {
    if (runs.length === 0) {
      setRunExecution(null);
      return;
    }
    const latestRun = runs[runs.length - 1];
    fetchRunExecution(latestRun.id);
  }, [runs, fetchRunExecution]);

  const attachmentsByMessage = useMemo(() => {
    return attachments.reduce<Record<string, Attachment[]>>((accumulator, attachment) => {
      accumulator[attachment.messageId] = [
        ...(accumulator[attachment.messageId] ?? []),
        attachment
      ];
      return accumulator;
    }, {});
  }, [attachments]);

  return {
    attachments,
    attachmentsByMessage,
    connectionStatus,
    conversation,
    conversationId,
    conversationSummaries,
    error,
    events,
    isCreatingConversation,
    isLoadingConversation,
    isSending,
    messages,
    openReviewTasks,
    reviewTasks,
    refreshConversations,
    runExecution,
    runs,
    sendMessage,
    selectConversation,
    startConversation,
    updateReviewTask
  };
}

function isArchitectureMode(value: unknown): value is ArchitectureMode {
  return (
    value === "centralized_orchestration"
    || value === "structured_workflow"
    || value === "decentralized_swarm"
  );
}

function getLastEventId(events: ProcessingEvent[]): string | null {
  return events.length > 0 ? events[events.length - 1].id : null;
}

function mergeEvents(
  currentEvents: ProcessingEvent[],
  incomingEvents: ProcessingEvent[]
): ProcessingEvent[] {
  const byId = new Map<string, ProcessingEvent>();
  for (const event of currentEvents) {
    byId.set(event.id, event);
  }
  for (const event of incomingEvents) {
    byId.set(event.id, event);
  }

  return Array.from(byId.values()).sort((left, right) => {
    const timeDifference =
      new Date(left.createdAt).getTime() - new Date(right.createdAt).getTime();
    return timeDifference === 0 ? left.id.localeCompare(right.id) : timeDifference;
  });
}

function mergeEventsForConversation(
  conversationId: string,
  currentEvents: ProcessingEvent[],
  incomingEvents: ProcessingEvent[]
): ProcessingEvent[] {
  return mergeEvents(
    currentEvents.filter((event) => event.conversationId === conversationId),
    incomingEvents.filter((event) => event.conversationId === conversationId)
  );
}
