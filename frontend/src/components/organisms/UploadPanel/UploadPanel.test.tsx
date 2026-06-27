import {
  describe, it, expect, vi,
} from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/server';
import { renderWithProviders } from '@/test/render';
import { UploadPanel } from './UploadPanel';

const BASE_URL = 'http://localhost:8000/api/v1';

// mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

function makeFile(name = 'test.pdf', type = 'application/pdf', sizeBytes = 1024) {
  return new File([new ArrayBuffer(sizeBytes)], name, { type });
}

describe('UploadPanel', () => {
  it('renders the dropzone', () => {
    renderWithProviders(<UploadPanel />);
    expect(screen.getByRole('button', { name: 'Upload PDF' })).toBeInTheDocument();
  });

  it('shows error for non-PDF files', async () => {
    renderWithProviders(<UploadPanel />);
    const file = makeFile('doc.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
    // simulate file input change via the hidden input
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Only PDF files are supported.');
    });
    // no upload call made
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('shows error for files over 50MB', async () => {
    renderWithProviders(<UploadPanel />);
    const file = makeFile('big.pdf', 'application/pdf', 51 * 1024 * 1024);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('File must be 50 MB or smaller.');
    });
  });

  it('shows processing status after successful upload', async () => {
    renderWithProviders(<UploadPanel />);
    const file = makeFile();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      // dropzone should be gone; at least one status element should be visible
      expect(screen.queryByRole('button', { name: 'Upload PDF' })).not.toBeInTheDocument();
      expect(screen.getAllByText(/Pending|Processing|Queued|Ready|Failed/i).length).toBeGreaterThan(0);
    });
  });

  it('shows upload error when API fails', async () => {
    server.use(
      http.post(`${BASE_URL}/documents`, () => HttpResponse.json({ message: 'Server error' }, { status: 500 })),
    );
    renderWithProviders(<UploadPanel />);
    const file = makeFile();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Upload failed');
    });
  });

  it('navigates to chat when document becomes ready', async () => {
    server.use(
      http.get(`${BASE_URL}/documents/:id`, () => HttpResponse.json({
        data: {
          document_id: '11111111-1111-1111-1111-111111111111',
          filename: 'test.pdf',
          status: 'ready',
          chunk_count: 42,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
        error: null,
      })),
    );
    renderWithProviders(<UploadPanel />);
    const file = makeFile();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/chat/11111111-1111-1111-1111-111111111111');
    });
  });

  it('shows retry button when document fails', async () => {
    server.use(
      http.get(`${BASE_URL}/documents/:id`, () => HttpResponse.json({
        data: {
          document_id: '11111111-1111-1111-1111-111111111111',
          filename: 'test.pdf',
          status: 'failed',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
        error: null,
      })),
    );
    renderWithProviders(<UploadPanel />);
    const file = makeFile();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
    });
  });
});
