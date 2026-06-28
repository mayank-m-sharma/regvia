import { http, HttpResponse } from 'msw';

const BASE_URL = 'http://localhost:8000/api/v1';

// eslint-disable-next-line import/prefer-default-export
export const handlers = [
  // Auth
  http.get(`${BASE_URL}/auth/login`, () => HttpResponse.json({
    data: { url: 'https://accounts.google.com/o/oauth2/auth?client_id=test', state: 'random-state-xyz' },
    error: null,
  })),

  http.post(`${BASE_URL}/auth/exchange`, () => HttpResponse.json({
    data: { token: 'test-jwt-token' },
    error: null,
  })),

  http.get(`${BASE_URL}/auth/me`, () => HttpResponse.json({
    data: {
      id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
      email: 'user@example.com',
      display_name: 'Test User',
      avatar_url: null,
    },
    error: null,
  })),

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

  // Chat sessions
  http.get(`${BASE_URL}/chat/sessions`, () => HttpResponse.json({
    data: [
      {
        id: '55555555-5555-5555-5555-555555555555',
        document_id: '11111111-1111-1111-1111-111111111111',
        document_filename: 'test.pdf',
        title: 'Data Retention Policy',
        created_at: '2024-01-01T00:00:00Z',
        last_message_at: '2024-01-02T10:00:00Z',
        message_count: 4,
      },
    ],
    error: null,
  })),

  http.post(`${BASE_URL}/chat/sessions`, () => HttpResponse.json({
    data: {
      id: '55555555-5555-5555-5555-555555555555',
      document_id: '11111111-1111-1111-1111-111111111111',
      document_filename: 'test.pdf',
      title: null,
      created_at: '2024-01-01T00:00:00Z',
      last_message_at: null,
      message_count: 0,
    },
    error: null,
  }, { status: 201 })),

  http.get(`${BASE_URL}/chat/sessions/:id`, ({ params }) => HttpResponse.json({
    data: {
      id: params.id,
      document_id: '11111111-1111-1111-1111-111111111111',
      document_filename: 'test.pdf',
      title: 'Data Retention Policy',
      created_at: '2024-01-01T00:00:00Z',
      last_message_at: '2024-01-02T10:00:00Z',
      messages: [
        {
          id: '66666666-6666-6666-6666-666666666666',
          role: 'user',
          content: 'What are the retention requirements?',
          citations: [],
          created_at: '2024-01-02T09:00:00Z',
        },
        {
          id: '77777777-7777-7777-7777-777777777777',
          role: 'assistant',
          content: 'Data must be retained for 5 years.',
          citations: [],
          created_at: '2024-01-02T09:01:00Z',
        },
      ],
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
