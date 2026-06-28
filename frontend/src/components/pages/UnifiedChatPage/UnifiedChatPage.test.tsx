import {
  describe, it, expect, vi, beforeEach, beforeAll,
} from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/render';
import { UnifiedChatPage } from './UnifiedChatPage';

// jsdom does not implement scrollIntoView — mock it globally for this suite.
beforeAll(() => {
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
});

const mockNavigate = vi.fn();
const mockUseParams = vi.fn<() => Record<string, string | undefined>>();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate, useParams: () => mockUseParams() };
});

const defaultProps = { dark: false, setDark: vi.fn() };

beforeEach(() => {
  vi.clearAllMocks();
  mockUseParams.mockReturnValue({});
});

describe('UnifiedChatPage', () => {
  it('renders in document mode by default with "Document Chat" button active', () => {
    renderWithProviders(<UnifiedChatPage {...defaultProps} />);

    const docBtn = screen.getByRole('button', { name: 'Document Chat' });
    expect(docBtn).toBeInTheDocument();
    // Active button carries bg-primary class
    expect(docBtn.className).toContain('bg-primary');
  });

  it('shows the document mode description text by default', () => {
    renderWithProviders(<UnifiedChatPage {...defaultProps} />);
    expect(
      screen.getByText(/Chat with a single PDF.*page citations/i),
    ).toBeInTheDocument();
  });

  it('switches to library mode when "Knowledge Library" button is clicked', async () => {
    renderWithProviders(<UnifiedChatPage {...defaultProps} />);

    await userEvent.click(screen.getByRole('button', { name: 'Knowledge Library' }));

    await waitFor(() => {
      expect(
        screen.getByText('Ask your Knowledge Library'),
      ).toBeInTheDocument();
    });
  });

  it('shows the library mode description text after switching', async () => {
    renderWithProviders(<UnifiedChatPage {...defaultProps} />);

    await userEvent.click(screen.getByRole('button', { name: 'Knowledge Library' }));

    await waitFor(() => {
      expect(
        screen.getByText(/Search across all documents/i),
      ).toBeInTheDocument();
    });
  });

  it('switches to library mode when the session has no document_id', async () => {
    const { http, HttpResponse } = await import('msw');
    const { server } = await import('@/test/server');

    const LIBRARY_SESSION = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';

    server.use(
      http.get(
        'http://localhost:8000/api/v1/chat/sessions/:id',
        () => HttpResponse.json({
          data: {
            id: LIBRARY_SESSION,
            document_id: null,
            document_filename: null,
            title: 'Library session',
            created_at: '2024-01-01T00:00:00Z',
            last_message_at: null,
            messages: [],
          },
          error: null,
        }),
      ),
    );

    mockUseParams.mockReturnValue({ sessionId: LIBRARY_SESSION });

    renderWithProviders(<UnifiedChatPage {...defaultProps} />);

    await waitFor(() => {
      const libBtn = screen.getByRole('button', { name: 'Knowledge Library' });
      expect(libBtn.className).toContain('bg-primary');
    });
  });

  it('stays in document mode when the session has a document_id', async () => {
    const DOC_SESSION = '55555555-5555-5555-5555-555555555555';
    mockUseParams.mockReturnValue({ sessionId: DOC_SESSION });

    // Default MSW handler returns a session with document_id set.
    renderWithProviders(<UnifiedChatPage {...defaultProps} />);

    await waitFor(() => {
      const docBtn = screen.getByRole('button', { name: 'Document Chat' });
      expect(docBtn.className).toContain('bg-primary');
    });
  });
});
