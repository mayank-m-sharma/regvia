import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/server';
import {
  uploadDocument, getDocumentStatus, sendMessage, getSummary, getLoginUrl, exchangeCode, getMe,
} from './index';
import { ApiError, ApiValidationError } from './errors';

const BASE_URL = 'http://localhost:8000/api/v1';

describe('API client', () => {
  describe('getLoginUrl', () => {
    it('returns url and state', async () => {
      const result = await getLoginUrl();
      expect(result.url).toContain('accounts.google.com');
      expect(result.state).toBe('random-state-xyz');
    });
  });

  describe('exchangeCode', () => {
    it('returns a JWT token', async () => {
      const token = await exchangeCode('auth-code-123');
      expect(token).toBe('test-jwt-token');
    });
  });

  describe('getMe', () => {
    it('returns user info', async () => {
      const user = await getMe();
      expect(user.email).toBe('user@example.com');
      expect(user.display_name).toBe('Test User');
    });
  });

  describe('uploadDocument', () => {
    it('returns a Document on success', async () => {
      const file = new File(['%PDF-1.4'], 'test.pdf', { type: 'application/pdf' });
      const doc = await uploadDocument(file);
      expect(doc.document_id).toBe('11111111-1111-1111-1111-111111111111');
      expect(doc.status).toBe('pending');
    });

    it('throws ApiValidationError on malformed response', async () => {
      server.use(
        http.post(`${BASE_URL}/documents`, () => HttpResponse.json({ data: { bad: 'schema' }, error: null })),
      );
      const file = new File(['%PDF'], 'test.pdf', { type: 'application/pdf' });
      await expect(uploadDocument(file)).rejects.toThrow(ApiValidationError);
    });
  });

  describe('getDocumentStatus', () => {
    it('returns document with status', async () => {
      const doc = await getDocumentStatus('11111111-1111-1111-1111-111111111111');
      expect(doc.status).toBe('ready');
      expect(doc.chunk_count).toBe(42);
    });
  });

  describe('sendMessage', () => {
    it('returns message with citations', async () => {
      const msg = await sendMessage({
        document_id: '11111111-1111-1111-1111-111111111111',
        session_id: null,
        question: 'What are the data retention requirements?',
      });
      expect(msg.found_in_document).toBe(true);
      expect(msg.citations).toHaveLength(1);
    });
  });

  describe('getSummary', () => {
    it('returns structured summary', async () => {
      const summary = await getSummary('11111111-1111-1111-1111-111111111111');
      expect(summary.obligations).toHaveLength(1);
      expect(summary.risks[0]?.severity).toBe('high');
      expect(summary.gaps[0]?.chunk_id).toBeNull();
    });
  });

  describe('ApiError', () => {
    it('is thrown when envelope contains an error', async () => {
      server.use(
        http.get(`${BASE_URL}/documents/:id`, () => HttpResponse.json({
          data: null,
          error: { message: 'Document not found', code: 'DOCUMENT_NOT_FOUND' },
        })),
      );
      await expect(getDocumentStatus('nonexistent')).rejects.toThrow(ApiError);
    });
  });
});
