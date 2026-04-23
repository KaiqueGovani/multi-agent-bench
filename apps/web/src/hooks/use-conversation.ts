"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  createConversation,
  getConversation,
  getConversationEvents,
  getConversationMessages,
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
  Message,
  ProcessingEvent,
  ReviewTask,
  ReviewTaskStatus,
  Run
} from "@/lib/types";

type ConnectionStatus = "idle" | "connecting" | "open" | "closed" | "error" | "reconnecting";

export function useConversation(architectureMode: ArchitectureMode) {
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

  const refreshConversations = useCallback(async () => {
    try {
      const response = await listConversations();
      setConversationSummaries(response.conversations);
      return response.conversations;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to refresh conversations");
      return [];
    }
  }, []);

  const refreshOpenReviewTasks = useCallback(async () => {
    try {
      const response = await listOpenReviewTasks();
      setOpenReviewTasks(response.reviewTasks);
      return response.reviewTasks;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to refresh reviews");
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
        setError(caught instanceof Error ? caught.message : "Failed to load conversation");
      }
    } finally {
      if (activeConversationIdRef.current === id) {
        setIsLoadingConversation(false);
      }
    }
  }, []);

  const refreshMessages = useCallback(async (id: string) => {
    const response = await getConversationMessages(id);
    if (activeConversationIdRef.current !== id) {
      return;
    }
    setMessages(response.messages);
    setAttachments(response.attachments);
    void refreshConversations();
  }, [refreshConversations]);

  const refreshConversationDetail = useCallback(async (id: string) => {
    try {
      const detail = await getConversation(id);
      if (activeConversationIdRef.current !== id) {
        return null;
      }
      setConversation(detail.conversation);
      setMessages(detail.messages);
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
        setError(caught instanceof Error ? caught.message : "Failed to refresh conversation");
      }
      return null;
    }
  }, [refreshConversations]);

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
      setError(caught instanceof Error ? caught.message : "Failed to refresh events");
      return [];
    }
  }, []);

  const startConversation = useCallback(async () => {
    setError(null);
    setIsCreatingConversation(true);
    try {
      const created = await createConversation(architectureMode);
      await loadConversation(created.conversationId);
      await refreshConversations();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to create conversation");
    } finally {
      setIsCreatingConversation(false);
    }
  }, [architectureMode, loadConversation, refreshConversations]);

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
      note: string
    ) => {
      setError(null);
      await resolveReviewTaskRequest(reviewTaskId, {
        note: note.trim() || undefined,
        resolvedBy: "local_human_reviewer",
        status
      });
      await refreshOpenReviewTasks();
      if (conversationId) {
        await refreshConversationDetail(conversationId);
      }
    },
    [conversationId, refreshConversationDetail, refreshOpenReviewTasks]
  );

  const sendMessage = useCallback(
    async (text: string, files: File[]) => {
      if (!conversationId || (!text.trim() && files.length === 0)) {
        return;
      }
      setIsSending(true);
      setError(null);
      try {
        await sendMultipartMessage(conversationId, text.trim(), files, architectureMode);
        await refreshMessages(conversationId);
        window.setTimeout(() => {
          void refreshMessages(conversationId);
          void refreshConversations();
        }, 1600);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Failed to send message");
      } finally {
        setIsSending(false);
      }
    },
    [architectureMode, conversationId, refreshConversations, refreshMessages]
  );

  useEffect(() => {
    void refreshConversations();
    void refreshOpenReviewTasks();
  }, [refreshConversations, refreshOpenReviewTasks]);

  useEffect(() => {
    if (!conversationId) {
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

          if (event.eventType === "response.final" || event.eventType === "processing.completed") {
            void refreshConversationDetail(conversationId);
          }
        },
        (status) => {
          setConnectionStatus(status);
          if (status === "open") {
            void refreshEvents(conversationId);
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
  }, [conversationId, refreshConversationDetail, refreshEvents]);

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
