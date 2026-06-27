import { http, HttpResponse } from 'msw';

const BASE_URL = 'http://localhost:8000/api/v1';

// eslint-disable-next-line import/prefer-default-export
export const handlers = [
  // Upload document
  http.post(`${BASE_URL}/documents`, () => HttpResponse.json({
    data: {
      document_id: '11111111-1111-1111-1111-111111111111',
      filename: 'test.pdf',
      status: 'pending',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    error: null,
  }, { status: 202 })),

  // Get document status
  http.get(`${BASE_URL}/documents/:id`, ({ params }) => HttpResponse.json({
    data: {
      document_id: params.id,
      filename: 'test.pdf',
      status: 'ready',
      chunk_count: 42,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    error: null,
  })),

  // Chat
  http.post(`${BASE_URL}/chat`, () => HttpResponse.json({
    data: {
      session_id: '22222222-2222-2222-2222-222222222222',
      message_id: '33333333-3333-3333-3333-333333333333',
      answer: 'The data retention requirement is 5 years.',
      citations: [
        {
          chunk_id: '44444444-4444-4444-4444-444444444444',
          page_number: 7,
          excerpt: '...data shall be retained for a minimum period of 5 years...',
        },
      ],
      found_in_document: true,
    },
    error: null,
  })),

  // Summary
  http.post(`${BASE_URL}/documents/:id/summary`, ({ params }) => HttpResponse.json({
    data: {
      document_id: params.id,
      obligations: [{ text: 'Retain data for 5 years', page_number: 3, chunk_id: '44444444-4444-4444-4444-444444444444' }],
      risks: [{
        text: 'Non-compliance penalty', severity: 'high', page_number: 5, chunk_id: '44444444-4444-4444-4444-444444444444',
      }],
      gaps: [{ text: 'Missing incident response plan', page_number: null, chunk_id: null }],
      recommendations: [{ text: 'Implement data retention policy', priority: 'high' }],
      generated_at: '2024-01-01T00:00:00Z',
    },
    error: null,
  })),
];
