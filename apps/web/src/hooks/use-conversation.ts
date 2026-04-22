"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createConversation,
  getConversation,
  getConversationEvents,
  getConversationMessages,
  sendMessage as sendMultipartMessage
} from "@/lib/api/client";
import { openConversationEventStream } from "@/lib/sse/events";
import type { Attachment, Message, ProcessingEvent } from "@/lib/types";

type ConnectionStatus = "idle" | "connecting" | "open" | "closed" | "error";

export function useConversation() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [events, setEvents] = useState<ProcessingEvent[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("idle");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshMessages = useCallback(async (id: string) => {
    const response = await getConversationMessages(id);
    setMessages(response.messages);
    setAttachments(response.attachments);
  }, []);

  const refreshEvents = useCallback(async (id: string) => {
    try {
      const response = await getConversationEvents(id);
      setEvents((current) => mergeEvents(current, response));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to refresh events");
    }
  }, []);

  const startConversation = useCallback(async () => {
    setError(null);
    const created = await createConversation();
    setConversationId(created.conversationId);
    const detail = await getConversation(created.conversationId);
    setMessages(detail.messages);
    setAttachments(detail.attachments);
    setEvents(detail.events);
  }, []);

  const sendMessage = useCallback(
    async (text: string, files: File[]) => {
      if (!conversationId || (!text.trim() && files.length === 0)) {
        return;
      }
      setIsSending(true);
      setError(null);
      try {
        await sendMultipartMessage(conversationId, text.trim(), files);
        await refreshMessages(conversationId);
        window.setTimeout(() => {
          void refreshMessages(conversationId);
        }, 1600);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Failed to send message");
      } finally {
        setIsSending(false);
      }
    },
    [conversationId, refreshMessages]
  );

  useEffect(() => {
    if (!conversationId) {
      return;
    }

    const source = openConversationEventStream(
      conversationId,
      (event) => {
        setEvents((current) => {
          return mergeEvents(current, [event]);
        });

        if (event.eventType === "response.final" || event.eventType === "processing.completed") {
          void refreshMessages(conversationId);
        }
      },
      (status) => {
        setConnectionStatus(status);
        if (status === "open") {
          void refreshEvents(conversationId);
        }
      }
    );

    void refreshEvents(conversationId);

    return () => {
      setConnectionStatus("closed");
      source.close();
    };
  }, [conversationId, refreshEvents, refreshMessages]);

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
    attachmentsByMessage,
    connectionStatus,
    conversationId,
    error,
    events,
    isSending,
    messages,
    sendMessage,
    startConversation
  };
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
