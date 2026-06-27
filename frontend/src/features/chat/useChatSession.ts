import { useState, useCallback } from 'react';
import { useUIStore } from '@/store';
import { useSSE } from '@/shared/hooks/useSSE';
import { sendMessage } from '@/shared/api';
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

export function useChatSession(documentId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const { activeSessionId, setActiveSessionId, setStreamingMessageId } = useUIStore();
  const { connect } = useSSE(API_BASE);

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
      if (isStreaming) return;

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
        sendMessage({ document_id: documentId, session_id: activeSessionId, question })
          .then((msg: Message) => {
            setActiveSessionId(msg.session_id);
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
          { document_id: documentId, session_id: activeSessionId, question },
          {
            onToken: (token) => appendToken(assistantMsgId, token),
            onCitations: (raw) => {
              citationsReceived = raw as Citation[];
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
      isStreaming, documentId, activeSessionId, connect,
      appendToken, finalise, markError, setActiveSessionId, setStreamingMessageId,
    ],
  );

  return { messages, isStreaming, sendQuestion };
}
