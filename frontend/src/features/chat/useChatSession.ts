import { useState, useCallback, useEffect } from 'react';
import { useUIStore } from '@/store';
import { useSSE } from '@/shared/hooks/useSSE';
import { sendMessage, getSession } from '@/shared/api';
import type { Citation, Message } from '@/shared/types/types';

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations: Citation[]
  foundInDocument: boolean
  streaming: boolean
  error: boolean
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)
  ?? 'http://localhost:8000/api/v1';

export function useChatSession(sessionId: string | null, documentId: string | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const { setStreamingMessageId } = useUIStore();
  const { connect } = useSSE(API_BASE);

  // Load history when sessionId is provided
  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      setHistoryLoaded(false);
      return;
    }
    setHistoryLoaded(false);
    getSession(sessionId)
      .then((detail) => {
        const loaded: ChatMessage[] = detail.messages.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          citations: m.citations,
          foundInDocument: true,
          streaming: false,
          error: false,
        }));
        setMessages(loaded);
        setHistoryLoaded(true);
      })
      .catch(() => {
        setMessages([]);
        setHistoryLoaded(true);
      });
  }, [sessionId]);

  const appendToken = useCallback((msgId: string, token: string) => {
    setMessages((prev) => prev.map(
      (m) => (m.id === msgId ? { ...m, content: m.content + token } : m),
    ));
  }, []);

  const finalise = useCallback(
    (msgId: string, citations: Citation[], foundInDocument: boolean) => {
      setMessages((prev) => prev.map((m) => (m.id === msgId ? {
        ...m, citations, foundInDocument, streaming: false,
      } : m)));
      setIsStreaming(false);
      setStreamingMessageId(null);
    },
    [setStreamingMessageId],
  );

  const markError = useCallback((msgId: string) => {
    setMessages((prev) => prev.map(
      (m) => (m.id === msgId ? { ...m, streaming: false, error: true } : m),
    ));
    setIsStreaming(false);
    setStreamingMessageId(null);
  }, [setStreamingMessageId]);

  const sendQuestion = useCallback(
    (question: string) => {
      if (isStreaming || !documentId) return;

      const userMsgId = crypto.randomUUID();
      const assistantMsgId = crypto.randomUUID();

      setMessages((prev) => [
        ...prev,
        {
          id: userMsgId,
          role: 'user',
          content: question,
          citations: [],
          foundInDocument: true,
          streaming: false,
          error: false,
        },
        {
          id: assistantMsgId,
          role: 'assistant',
          content: '',
          citations: [],
          foundInDocument: true,
          streaming: true,
          error: false,
        },
      ]);

      setIsStreaming(true);
      setStreamingMessageId(assistantMsgId);

      let citationsReceived: Citation[] = [];
      let doneReceived = false;

      const fallback = () => {
        if (doneReceived) return;
        sendMessage({
          document_id: documentId,
          session_id: sessionId,
          question,
        })
          .then((msg: Message) => {
            setMessages((prev) => prev.map((m) => (m.id === assistantMsgId ? {
              ...m,
              content: msg.answer,
              citations: msg.citations,
              foundInDocument: msg.found_in_document,
              streaming: false,
            } : m)));
            setIsStreaming(false);
            setStreamingMessageId(null);
          })
          .catch(() => markError(assistantMsgId));
      };

      try {
        connect(
          '/chat/stream',
          { document_id: documentId, session_id: sessionId, question },
          {
            onToken: (token) => appendToken(assistantMsgId, token),
            onCitations: (raw) => {
              const payload = raw as unknown as { citations: Citation[] } | Citation[];
              citationsReceived = Array.isArray(payload) ? payload : payload.citations ?? [];
            },
            onDone: () => {
              doneReceived = true;
              finalise(assistantMsgId, citationsReceived, citationsReceived.length > 0);
            },
            onError: fallback,
          },
        );
      } catch {
        markError(assistantMsgId);
      }
    },
    [
      isStreaming, documentId, sessionId, connect,
      appendToken, finalise, markError, setStreamingMessageId,
    ],
  );

  return {
    messages, isStreaming, historyLoaded, sendQuestion,
  };
}
