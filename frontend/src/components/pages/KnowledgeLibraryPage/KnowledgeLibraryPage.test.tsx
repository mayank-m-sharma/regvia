import {
  describe, it, expect, vi,
} from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/render';
import { KnowledgeLibraryPage } from './KnowledgeLibraryPage';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

describe('KnowledgeLibraryPage', () => {
  it('renders the page heading', () => {
    renderWithProviders(
      <KnowledgeLibraryPage dark={false} setDark={vi.fn()} />,
    );
    expect(screen.getByText('Knowledge Library')).toBeInTheDocument();
  });

  it('shows a loading spinner initially', () => {
    renderWithProviders(
      <KnowledgeLibraryPage dark={false} setDark={vi.fn()} />,
    );
    expect(document.querySelector('svg.animate-spin')).toBeInTheDocument();
  });

  it('renders the document table after loading', async () => {
    renderWithProviders(
      <KnowledgeLibraryPage dark={false} setDark={vi.fn()} />,
    );
    await waitFor(() => {
      expect(screen.getByText('gdpr-policy.pdf')).toBeInTheDocument();
    });
    expect(screen.getByText('iso27001.pdf')).toBeInTheDocument();
  });

  it('shows ready status for a ready document', async () => {
    renderWithProviders(
      <KnowledgeLibraryPage dark={false} setDark={vi.fn()} />,
    );
    await waitFor(() => {
      expect(screen.getByText('Ready')).toBeInTheDocument();
    });
  });

  it('shows training status for a processing document', async () => {
    renderWithProviders(
      <KnowledgeLibraryPage dark={false} setDark={vi.fn()} />,
    );
    await waitFor(() => {
      expect(screen.getByText('Training…')).toBeInTheDocument();
    });
  });

  it('navigates back to chat when back link is clicked', async () => {
    renderWithProviders(
      <KnowledgeLibraryPage dark={false} setDark={vi.fn()} />,
    );
    await userEvent.click(screen.getByText('← Back to chat'));
    expect(mockNavigate).toHaveBeenCalledWith('/chat');
  });

  it('shows empty state when GET /documents returns empty list', async () => {
    const { http, HttpResponse } = await import('msw');
    const { server } = await import('@/test/server');
    server.use(
      http.get('http://localhost:8000/api/v1/documents', () => HttpResponse.json({
        data: [],
        error: null,
      })),
    );
    renderWithProviders(
      <KnowledgeLibraryPage dark={false} setDark={vi.fn()} />,
    );
    await waitFor(() => {
      expect(screen.getByText(/no documents in your library yet/i)).toBeInTheDocument();
    });
  });

  it('has an accessible upload drop zone', () => {
    renderWithProviders(
      <KnowledgeLibraryPage dark={false} setDark={vi.fn()} />,
    );
    expect(screen.getByRole('button', { name: /upload pdf files/i })).toBeInTheDocument();
  });
});
