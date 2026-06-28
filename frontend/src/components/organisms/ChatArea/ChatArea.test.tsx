import {
  describe, it, expect, vi, beforeAll,
} from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/render';
import type { ChatMessage } from '@/features/chat';
import { ChatArea } from './ChatArea';

// jsdom does not implement scrollIntoView — mock it globally for this suite.
beforeAll(() => {
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
});

const baseProps = {
  messages: [] as ChatMessage[],
  hasDocument: false,
  isDocumentReady: false,
  onFile: vi.fn(),
  onFileError: vi.fn(),
  onSend: vi.fn(),
};

function makeMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role: 'user',
    content: 'Hello',
    citations: [],
    foundInDocument: true,
    streaming: false,
    error: false,
    ...overrides,
  };
}

describe('ChatArea', () => {
  describe('document mode — no document', () => {
    it('shows "Document Chat" heading', () => {
      renderWithProviders(<ChatArea {...baseProps} />);
      expect(screen.getByText('Document Chat')).toBeInTheDocument();
    });

    it('shows the drag-and-drop zone', () => {
      renderWithProviders(<ChatArea {...baseProps} />);
      expect(screen.getByText('Drag & drop a PDF here')).toBeInTheDocument();
    });

    it('shows hint about Knowledge Library mode', () => {
      renderWithProviders(<ChatArea {...baseProps} />);
      expect(
        screen.getByText(/switch to Knowledge Library mode/i),
      ).toBeInTheDocument();
    });
  });

  describe('document mode — document uploading (not ready)', () => {
    it('shows "Training your document…" message', () => {
      renderWithProviders(
        <ChatArea {...baseProps} hasDocument isDocumentReady={false} />,
      );
      expect(screen.getByText('Training your document…')).toBeInTheDocument();
    });
  });

  describe('document mode — document ready, no messages', () => {
    it('shows "Document ready" status text', () => {
      renderWithProviders(
        <ChatArea {...baseProps} hasDocument isDocumentReady />,
      );
      expect(
        screen.getByText('Document ready — ask anything'),
      ).toBeInTheDocument();
    });

    it('shows suggestion chips', () => {
      renderWithProviders(
        <ChatArea {...baseProps} hasDocument isDocumentReady />,
      );
      expect(
        screen.getByText('What are the key obligations in this document?'),
      ).toBeInTheDocument();
    });

    it('calls onSend when a suggestion chip is clicked', async () => {
      const onSend = vi.fn();
      renderWithProviders(
        <ChatArea {...baseProps} hasDocument isDocumentReady onSend={onSend} />,
      );
      await userEvent.click(
        screen.getByText('What are the key obligations in this document?'),
      );
      expect(onSend).toHaveBeenCalledWith(
        'What are the key obligations in this document?',
      );
    });
  });

  describe('library mode', () => {
    it('shows "Ask your Knowledge Library" heading', () => {
      renderWithProviders(
        <ChatArea {...baseProps} mode="library" />,
      );
      expect(
        screen.getByText('Ask your Knowledge Library'),
      ).toBeInTheDocument();
    });

    it('shows library-specific suggestions', () => {
      renderWithProviders(
        <ChatArea {...baseProps} mode="library" />,
      );
      expect(
        screen.getByText(
          'What compliance requirements are common across my documents?',
        ),
      ).toBeInTheDocument();
    });

    it('shows the manage library button and calls onManageLibrary on click', async () => {
      const onManageLibrary = vi.fn();
      renderWithProviders(
        <ChatArea
          {...baseProps}
          mode="library"
          onManageLibrary={onManageLibrary}
        />,
      );
      const btn = screen.getByRole('button', {
        name: /upload.*manage your library/i,
      });
      expect(btn).toBeInTheDocument();
      await userEvent.click(btn);
      expect(onManageLibrary).toHaveBeenCalledOnce();
    });
  });

  describe('messages', () => {
    it('renders provided messages', () => {
      const messages: ChatMessage[] = [
        makeMessage({ role: 'user', content: 'What are the deadlines?' }),
        makeMessage({
          role: 'assistant',
          content: 'The deadline is 31 December.',
        }),
      ];
      renderWithProviders(
        <ChatArea {...baseProps} hasDocument isDocumentReady messages={messages} />,
      );
      expect(screen.getByText('What are the deadlines?')).toBeInTheDocument();
      expect(
        screen.getByText('The deadline is 31 December.'),
      ).toBeInTheDocument();
    });
  });
});
