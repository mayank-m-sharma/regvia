import {
  describe, it, expect, vi, beforeEach,
} from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { getSession } from '@/shared/api';
import { useChatSession } from './useChatSession';

// Mock useSSE so we can control when streaming callbacks are invoked.
const mockConnect = vi.fn();
vi.mock('@/shared/hooks/useSSE', () => ({
  useSSE: () => ({ connect: mockConnect, disconnect: vi.fn() }),
}));

// Mock the API layer — we control responses per test.
vi.mock('@/shared/api', async () => {
  const actual = await vi.importActual<typeof import('@/shared/api')>('@/shared/api');
  return { ...actual, getSession: vi.fn(), sendMessage: vi.fn() };
});

const SESSION_ID = '55555555-5555-5555-5555-555555555555';
const DOC_ID = '11111111-1111-1111-1111-111111111111';

const SESSION_DETAIL = {
  id: SESSION_ID,
  document_id: DOC_ID,
  document_filename: 'test.pdf',
  title: 'Data Retention Policy',
  created_at: '2024-01-01T00:00:00Z',
  last_message_at: '2024-01-02T10:00:00Z',
  messages: [
    {
      id: '66666666-6666-6666-6666-666666666666',
      role: 'user' as const,
      content: 'What are the retention requirements?',
      citations: [],
      created_at: '2024-01-02T09:00:00Z',
    },
    {
      id: '77777777-7777-7777-7777-777777777777',
      role: 'assistant' as const,
      content: 'Data must be retained for 5 years.',
      citations: [],
      created_at: '2024-01-02T09:01:00Z',
    },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  (getSession as ReturnType<typeof vi.fn>).mockResolvedValue(SESSION_DETAIL);
});

describe('useChatSession', () => {
  it('returns empty messages and historyLoaded=false initially when sessionId is null', () => {
    const { result } = renderHook(() => useChatSession(null, null));
    expect(result.current.messages).toHaveLength(0);
    expect(result.current.historyLoaded).toBe(false);
  });

  it('calls getSession when a sessionId is provided', async () => {
    renderHook(() => useChatSession(SESSION_ID, DOC_ID));
    await waitFor(() => {
      expect(getSession).toHaveBeenCalledWith(SESSION_ID);
    });
  });

  it('populates messages from the loaded session history', async () => {
    const { result } = renderHook(() => useChatSession(SESSION_ID, DOC_ID));
    await waitFor(() => {
      expect(result.current.messages).toHaveLength(2);
    });
    expect(result.current.messages[0]?.content).toBe(
      'What are the retention requirements?',
    );
    expect(result.current.messages[0]?.role).toBe('user');
    expect(result.current.messages[1]?.content).toBe(
      'Data must be retained for 5 years.',
    );
    expect(result.current.historyLoaded).toBe(true);
  });

  it('clears messages when sessionId changes before loading new history', async () => {
    const { result, rerender } = renderHook(
      ({ sid }: { sid: string | null }) => useChatSession(sid, DOC_ID),
      { initialProps: { sid: SESSION_ID } },
    );

    // Wait for first session to load.
    await waitFor(() => {
      expect(result.current.messages).toHaveLength(2);
    });

    // Change sessionId — messages should clear synchronously.
    const NEW_SESSION = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
    (getSession as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...SESSION_DETAIL,
      id: NEW_SESSION,
      messages: [],
    });

    rerender({ sid: NEW_SESSION });

    // After the re-render (before the new async response) messages must be empty.
    expect(result.current.messages).toHaveLength(0);
    expect(result.current.historyLoaded).toBe(false);
  });

  it('adds user and assistant messages optimistically when sendQuestion is called', async () => {
    // Make connect call onError immediately so the fallback path fires and
    // streaming state is cleaned up — keeping this test focused on the
    // optimistic message addition rather than the streaming lifecycle.
    mockConnect.mockImplementation(
      (_path: string, _body: unknown, handlers: { onError: (m: string) => void }) => {
        handlers.onError('test error');
      },
    );

    const { result } = renderHook(() => useChatSession(null, DOC_ID));

    result.current.sendQuestion('What are the key risks?');

    await waitFor(() => {
      expect(result.current.messages.length).toBeGreaterThanOrEqual(2);
    });

    const userMsg = result.current.messages.find((m) => m.role === 'user');
    const assistantMsg = result.current.messages.find((m) => m.role === 'assistant');
    expect(userMsg?.content).toBe('What are the key risks?');
    expect(assistantMsg).toBeDefined();
  });
});
