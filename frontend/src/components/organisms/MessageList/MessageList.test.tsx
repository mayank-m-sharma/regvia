import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/test/render';
import { MessageList } from './MessageList';
import type { ChatMessage } from '@/features/chat';

function makeMsg(overrides: Partial<ChatMessage>): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role: 'assistant',
    content: 'Test answer',
    citations: [],
    foundInDocument: true,
    streaming: false,
    error: false,
    ...overrides,
  };
}

describe('MessageList', () => {
  it('shows empty state when no messages', () => {
    renderWithProviders(<MessageList messages={[]} />);
    expect(screen.getByText(/ask a question/i)).toBeInTheDocument();
  });

  it('renders user and assistant bubbles', () => {
    const msgs = [
      makeMsg({ role: 'user', content: 'What are the obligations?' }),
      makeMsg({ role: 'assistant', content: 'The obligations are...' }),
    ];
    renderWithProviders(<MessageList messages={msgs} />);
    expect(screen.getByText('What are the obligations?')).toBeInTheDocument();
    expect(screen.getByText('The obligations are...')).toBeInTheDocument();
  });

  it('renders citations under assistant messages', () => {
    const msgs = [
      makeMsg({
        citations: [{ chunk_id: '44444444-4444-4444-4444-444444444444', page_number: 7, excerpt: 'data shall be retained for 5 years' }],
      }),
    ];
    renderWithProviders(<MessageList messages={msgs} />);
    expect(screen.getByText(/p\.7/)).toBeInTheDocument();
    expect(screen.getByText(/data shall be retained/)).toBeInTheDocument();
  });

  it('styles "not found" messages distinctly', () => {
    const msgs = [makeMsg({ foundInDocument: false, content: 'I could not find this information in the document.' })];
    renderWithProviders(<MessageList messages={msgs} />);
    const bubble = screen.getByText(/could not find/i).closest('div');
    expect(bubble).toHaveClass('italic');
  });
});
