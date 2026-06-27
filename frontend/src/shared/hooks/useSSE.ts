import { useCallback, useRef } from 'react';

export interface SSEHandlers {
  onToken: (token: string) => void
  onCitations: (citations: unknown[]) => void
  onDone: () => void
  onError: (message: string) => void
}

function parseLine(
  line: string,
  eventType: string,
  handlers: SSEHandlers,
): string {
  if (line.startsWith('event: ')) {
    return line.slice(7).trim();
  }
  if (line.startsWith('data: ')) {
    const data = line.slice(6).trim();
    if (data) {
      try {
        const parsed = JSON.parse(data) as Record<string, unknown>;
        if (eventType === 'token') handlers.onToken((parsed.token as string) ?? '');
        else if (eventType === 'citations') handlers.onCitations((parsed.citations as unknown[]) ?? []);
        else if (eventType === 'done') handlers.onDone();
        else if (eventType === 'error') handlers.onError((parsed.message as string) ?? 'Unknown error');
      } catch {
        // malformed JSON line — skip
      }
      return '';
    }
  }
  return eventType;
}

export function useSSE(baseUrl: string) {
  const esRef = useRef<EventSource | null>(null);

  const connect = useCallback(
    (path: string, body: Record<string, unknown>, handlers: SSEHandlers) => {
      const url = `${baseUrl}${path}`;

      fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
        .then(async (res) => {
          if (!res.ok || !res.body) {
            handlers.onError('Stream connection failed');
            return;
          }
          const reader = res.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          // eslint-disable-next-line no-constant-condition
          while (true) {
            // eslint-disable-next-line no-await-in-loop
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() ?? '';

            let eventType = '';
            lines.forEach((line) => {
              eventType = parseLine(line, eventType, handlers);
            });
          }
        })
        .catch(() => handlers.onError('Stream connection failed'));
    },
    [baseUrl],
  );

  const disconnect = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
  }, []);

  return { connect, disconnect };
}
