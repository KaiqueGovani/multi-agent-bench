"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  createConversation,
  getConversation,
  getConversationEvents,
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
  Run
} from "@/lib/types";

type ConnectionStatus = "idle" | "connecting" | "open" | "closed" | "error" | "reconnecting";

export function useConversation(
  architectureMode: ArchitectureMode,
  executionMode: ExecutionMode = "real",
) {
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
  const detailRequestRef = useRef(0);
  const appliedDetailRequestRef = useRef(0);

  /** Tracks when the last refreshConversationDetail was triggered, for debouncing. */
  const lastRefreshTsRef = useRef(0);

  /** Tracks streaming message runIds with creation timestamps for timeout cleanup. */
  const streamingTimestampsRef = useRef(new Map<string, number>());

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
    const request = ++detailRequestRef.current;
    appliedDetailRequestRef.current = request;
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
    lastEventIdRef.current = null;

    try {
      const detail = await getConversation(id);
      if (activeConversationIdRef.current !== id || request < appliedDetailRequestRef.current) {
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
      if (activeConversationIdRef.current === id && request >= appliedDetailRequestRef.current) {
        setError(caught instanceof Error ? caught.message : "Falha ao carregar conversa");
      }
    } finally {
      if (activeConversationIdRef.current === id) {
        setIsLoadingConversation(false);
      }
    }
  }, []);

  const refreshConversationDetail = useCallback(async (id: string) => {
    if (activeConversationIdRef.current !== id) return null;
    const request = ++detailRequestRef.current;
    try {
      const detail = await getConversation(id);
      if (activeConversationIdRef.current !== id || request < appliedDetailRequestRef.current) {
        return null;
      }
      appliedDetailRequestRef.current = request;
      setConversation(detail.conversation);
      // Replace messages but keep any optimistic/streaming messages whose
      // persisted outbound counterpart hasn't landed yet. We use the
      // streaming id ("streaming-<runId>") to look up a matching outbound
      // by metadata.runtimeRunId — once the real message is present, the
      // streaming twin is dropped to avoid showing duplicates.
      setMessages((current) => {
        const realMessages = detail.messages;
        const persistedRunIds = new Set<string>(
          realMessages
            .filter((m) => m.direction === "outbound")
            .map((m) => readRuntimeRunId(m.metadata))
            .filter((value): value is string => Boolean(value)),
        );
        const remainingStreaming = current.filter((m) => {
          if (!m.id.startsWith("streaming-")) return false;
          const runId = m.id.slice("streaming-".length);
          if (persistedRunIds.has(runId)) {
            streamingTimestampsRef.current.delete(runId);
            return false;
          }
          return true;
        });
        return [...realMessages, ...remainingStreaming];
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
      if (activeConversationIdRef.current === id && request >= appliedDetailRequestRef.current) {
        setError(caught instanceof Error ? caught.message : "Falha ao atualizar conversa");
      }
      return null;
    }
  }, [refreshConversations, refreshOpenReviewTasks]);

  /** Debounced refresh: skips if another refresh happened within 500ms.
   *  Set `force` to true to bypass debounce (for critical events like run completion). */
  const debouncedRefreshDetail = useCallback(
    (id: string, force = false) => {
      const now = Date.now();
      if (!force && now - lastRefreshTsRef.current < 500) {
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
    appliedDetailRequestRef.current = ++detailRequestRef.current;
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

        await sendMultipartMessage(
          targetConversationId, text.trim(), files, activeArchitectureMode, executionMode,
        );
        await refreshConversationDetail(targetConversationId);
        
        // For all_architectures mode, add more frequent refreshes to catch parallel runs
        const isMultiArchitecture = activeArchitectureMode === "all_architectures";
        if (isMultiArchitecture) {
          // Refresh at 500ms, 1s, 2s, 3s to catch all parallel runs completing
          for (const delay of [500, 1000, 2000, 3000]) {
            window.setTimeout(() => {
              void refreshConversationDetail(targetConversationId);
            }, delay);
          }
          // Final refresh for conversations list
          window.setTimeout(() => {
            void refreshConversations();
          }, 3500);
        } else {
          window.setTimeout(() => {
            void refreshConversationDetail(targetConversationId);
            void refreshConversations();
          }, 1600);
        }
      } catch (caught) {
        // Remove optimistic message on error
        setMessages((prev) => prev.filter((m) => m.id !== optimisticId));
        setError(caught instanceof Error ? caught.message : "Falha ao enviar mensagem");
        // Let the composer retain its draft and attachment previews after rejection.
        throw caught;
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
    ],
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
          const payloadArchitectureMode = isArchitectureMode(event.payload?.architectureMode)
            ? event.payload.architectureMode
            : null;

          if (event.eventType === "processing.started" && event.messageId) {
            setMessages((current) => current.map((message) =>
              message.id === event.messageId && message.status === "accepted"
                ? { ...message, status: "processing" }
                : message,
            ));
          }

          if (
            event.eventType === "response.partial"
            && typeof event.payload?.contentText === "string"
            && payloadRunId
          ) {
            streamingTimestampsRef.current.set(payloadRunId, Date.now());
            setMessages((prev) => upsertStreamingMessage({
              architectureMode: payloadArchitectureMode,
              contentText: event.payload.contentText as string,
              conversationId,
              correlationId: event.correlationId,
              createdAt: event.createdAt,
              messages: prev,
              runId: payloadRunId,
              status: "processing",
            }));
          }

          if (
            event.eventType === "response.final"
            || event.eventType === "processing.completed"
            || event.eventType === "actor.failed"
            || event.eventType === "review.required"
          ) {
            // Don't remove the streaming bubble here. The persisted outbound
            // message lands via refreshConversationDetail, which then drops
            // the streaming twin (matched by runtimeRunId). Removing here
            // would cause the response to flicker — visible during streaming
            // → blank → visible again once the refresh completes.
            if (payloadRunId
              && event.eventType === "response.final"
              && typeof event.payload?.contentText === "string") {
              // Also fold in the final contentText so the bubble shows the
              // complete text immediately, even before the refresh.
              setMessages((prev) => upsertStreamingMessage({
                architectureMode: payloadArchitectureMode,
                contentText: event.payload.contentText as string,
                conversationId,
                correlationId: event.correlationId,
                createdAt: event.createdAt,
                messages: prev,
                runId: payloadRunId,
                status: "completed",
              }));
            }
            debouncedRefreshDetail(conversationId, true);
          }
        },
        (status) => {
          setConnectionStatus(status);
          if (status === "open") {
            void refreshEvents(conversationId);
          }
          // On SSE error/reconnect: purge ghost streaming messages
          if (status === "error" || status === "reconnecting") {
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
    };
  }, [conversationId, debouncedRefreshDetail, refreshConversationDetail, refreshEvents]);

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
    runs,
    sendMessage,
    selectConversation,
    startConversation,
    updateReviewTask
  };
}

function readRuntimeRunId(metadata: unknown): string | null {
  if (!metadata || typeof metadata !== "object") return null;
  const value = (metadata as Record<string, unknown>).runtimeRunId;
  return typeof value === "string" && value.length > 0 ? value : null;
}

function upsertStreamingMessage({
  architectureMode,
  contentText,
  conversationId,
  correlationId,
  createdAt,
  messages,
  runId,
  status,
}: {
  architectureMode: ArchitectureMode | null;
  contentText: string;
  conversationId: string;
  correlationId: string;
  createdAt: string;
  messages: Message[];
  runId: string;
  status: Message["status"];
}): Message[] {
  const streamingId = "streaming-" + runId;
  if (messages.some((message) =>
    message.direction === "outbound" && message.id !== streamingId
      && readRuntimeRunId(message.metadata) === runId,
  )) {
    return messages;
  }
  const existing = messages.findIndex((m) => m.id === streamingId);
  if (existing >= 0 && messages[existing].status === "completed" && status !== "completed") {
    return messages;
  }
  const existingMetadata = existing >= 0 ? messages[existing].metadata : null;
  const metadata = {
    ...(existingMetadata && typeof existingMetadata === "object" ? existingMetadata : {}),
    ...(architectureMode ? { architectureMode } : {}),
    runtimeRunId: runId,
  };
  if (existing >= 0) {
    const updated = [...messages];
    updated[existing] = {
      ...updated[existing],
      contentText,
      metadata,
      status,
    };
    return updated;
  }
  return [
    ...messages,
    {
      id: streamingId,
      conversationId,
      direction: "outbound",
      contentText,
      createdAtClient: null,
      createdAtServer: createdAt,
      status,
      correlationId,
      metadata,
    },
  ];
}

function isArchitectureMode(value: unknown): value is ArchitectureMode {
  return (
    value === "all_architectures"
    || value === "centralized_orchestration"
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
    if (timeDifference !== 0) return timeDifference;
    // Date truncates the API's fractional seconds to milliseconds.
    const leftFraction = left.createdAt.match(/\.(\d+)/)?.[1].padEnd(9, "0") ?? "000000000";
    const rightFraction = right.createdAt.match(/\.(\d+)/)?.[1].padEnd(9, "0") ?? "000000000";
    if (leftFraction !== rightFraction) return leftFraction.localeCompare(rightFraction);
    const leftRun = typeof left.payload.runId === "string" ? left.payload.runId : "";
    const rightRun = typeof right.payload.runId === "string" ? right.payload.runId : "";
    if (leftRun !== rightRun) return leftRun.localeCompare(rightRun);
    const leftSequence = left.payload.sequenceNo;
    const rightSequence = right.payload.sequenceNo;
    return (typeof leftSequence === "number" ? leftSequence : 0)
      - (typeof rightSequence === "number" ? rightSequence : 0)
      || left.id.localeCompare(right.id);
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
