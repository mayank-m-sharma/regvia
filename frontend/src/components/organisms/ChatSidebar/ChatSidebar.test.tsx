import {
  describe, it, expect, vi,
} from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/render';
import { ChatSidebar } from './ChatSidebar';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

describe('ChatSidebar', () => {
  it('shows loading spinner initially', () => {
    renderWithProviders(
      <ChatSidebar activeSessionId={null} onNewChat={vi.fn()} />,
    );
    expect(document.querySelector('svg.animate-spin')).toBeInTheDocument();
  });

  it('renders session titles after loading', async () => {
    renderWithProviders(
      <ChatSidebar activeSessionId={null} onNewChat={vi.fn()} />,
    );
    await waitFor(() => {
      expect(screen.getByText('Data Retention Policy')).toBeInTheDocument();
    });
  });

  it('highlights the active session', async () => {
    const SESSION_ID = '55555555-5555-5555-5555-555555555555';
    renderWithProviders(
      <ChatSidebar activeSessionId={SESSION_ID} onNewChat={vi.fn()} />,
    );
    await waitFor(() => {
      const btn = screen.getByText('Data Retention Policy').closest('button');
      expect(btn?.className).toContain('bg-primary/10');
    });
  });

  it('navigates to session on click', async () => {
    renderWithProviders(
      <ChatSidebar activeSessionId={null} onNewChat={vi.fn()} />,
    );
    await waitFor(() => screen.getByText('Data Retention Policy'));
    await userEvent.click(screen.getByText('Data Retention Policy'));
    expect(mockNavigate).toHaveBeenCalledWith(
      '/chat/55555555-5555-5555-5555-555555555555',
    );
  });

  it('calls onNewChat when + button is clicked', async () => {
    const onNewChat = vi.fn();
    renderWithProviders(
      <ChatSidebar activeSessionId={null} onNewChat={onNewChat} />,
    );
    await userEvent.click(screen.getByTitle('New chat'));
    expect(onNewChat).toHaveBeenCalledOnce();
  });

  it('shows empty state when there are no sessions', async () => {
    const { http, HttpResponse } = await import('msw');
    const { server } = await import('@/test/server');
    server.use(
      http.get('http://localhost:8000/api/v1/chat/sessions', () => HttpResponse.json({
        data: [],
        error: null,
      })),
    );
    renderWithProviders(
      <ChatSidebar activeSessionId={null} onNewChat={vi.fn()} />,
    );
    await waitFor(() => {
      expect(screen.getByText(/no chats yet/i)).toBeInTheDocument();
    });
  });
});
