"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createConversation,
  getConversation,
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
          if (current.some((item) => item.id === event.id)) {
            return current;
          }
          return [...current, event];
        });

        if (event.eventType === "response.final" || event.eventType === "processing.completed") {
          void refreshMessages(conversationId);
        }
      },
      setConnectionStatus
    );

    return () => {
      setConnectionStatus("closed");
      source.close();
    };
  }, [conversationId, refreshMessages]);

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
