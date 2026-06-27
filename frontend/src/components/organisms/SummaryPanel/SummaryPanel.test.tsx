import { describe, it, expect } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/server';
import { renderWithProviders } from '@/test/render';
import { SummaryPanel } from './SummaryPanel';

const BASE_URL = 'http://localhost:8000/api/v1';
const DOC_ID = '11111111-1111-1111-1111-111111111111';

describe('SummaryPanel', () => {
  it('shows generate button when no summary exists', () => {
    server.use(
      http.post(`${BASE_URL}/documents/:id/summary`, () => HttpResponse.json({ data: null, error: { message: 'Not found', code: 'NOT_FOUND' } }, { status: 404 })),
    );
    renderWithProviders(<SummaryPanel documentId={DOC_ID} />);
    expect(screen.getByRole('button', { name: /generate summary/i })).toBeInTheDocument();
  });

  it('renders all 4 sections after generation', async () => {
    renderWithProviders(<SummaryPanel documentId={DOC_ID} />);
    await userEvent.click(screen.getByRole('button', { name: /generate summary/i }));
    await waitFor(() => {
      expect(screen.getByText('Obligations')).toBeInTheDocument();
      expect(screen.getByText('Risks')).toBeInTheDocument();
      expect(screen.getByText('Gaps')).toBeInTheDocument();
      expect(screen.getByText('Recommendations')).toBeInTheDocument();
    });
  });

  it('shows skeleton loaders while generating', async () => {
    // Delay the MSW response so we can catch the loading state
    server.use(
      http.post(`${BASE_URL}/documents/:id/summary`, async () => {
        await new Promise((r) => { setTimeout(r, 100); });
        return HttpResponse.json({
          data: {
            document_id: DOC_ID,
            obligations: [{ text: 'Retain data for 5 years', page_number: 3, chunk_id: '44444444-4444-4444-4444-444444444444' }],
            risks: [{
              text: 'Non-compliance penalty', severity: 'high', page_number: 5, chunk_id: '44444444-4444-4444-4444-444444444444',
            }],
            gaps: [{ text: 'Missing incident response plan', page_number: null, chunk_id: null }],
            recommendations: [{ text: 'Implement data retention policy', priority: 'high' }],
            generated_at: '2024-01-01T00:00:00Z',
          },
          error: null,
        });
      }),
    );
    renderWithProviders(<SummaryPanel documentId={DOC_ID} />);
    await userEvent.click(screen.getByRole('button', { name: /generate summary/i }));
    // Skeleton sections appear (section headers rendered during loading)
    expect(screen.getByText('Obligations')).toBeInTheDocument();
  });

  it('shows severity badge for risks', async () => {
    renderWithProviders(<SummaryPanel documentId={DOC_ID} />);
    await userEvent.click(screen.getByRole('button', { name: /generate summary/i }));
    await waitFor(() => {
      expect(screen.getAllByText('High').length).toBeGreaterThan(0);
    });
  });

  it('shows page reference for items with page numbers', async () => {
    renderWithProviders(<SummaryPanel documentId={DOC_ID} />);
    await userEvent.click(screen.getByRole('button', { name: /generate summary/i }));
    await waitFor(() => {
      expect(screen.getAllByText(/p\.\d+/).length).toBeGreaterThan(0);
    });
  });

  it('shows error message when generation fails', async () => {
    server.use(
      http.post(`${BASE_URL}/documents/:id/summary`, () => HttpResponse.json({ data: null, error: { message: 'Server error', code: 'SUMMARY_FAILED' } }, { status: 500 })),
    );
    renderWithProviders(<SummaryPanel documentId={DOC_ID} />);
    await userEvent.click(screen.getByRole('button', { name: /generate summary/i }));
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/failed to generate/i);
    });
  });
});
