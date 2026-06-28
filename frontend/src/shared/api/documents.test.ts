import { describe, it, expect } from 'vitest';
import { getDocuments, addToLibrary } from './documents';

describe('documents API', () => {
  describe('getDocuments', () => {
    it('returns all user documents', async () => {
      const docs = await getDocuments();
      expect(docs).toHaveLength(2);
      expect(docs[0]?.filename).toBe('gdpr-policy.pdf');
      expect(docs[0]?.in_library).toBe(true);
    });

    it('includes size_bytes for each document', async () => {
      const docs = await getDocuments();
      expect(docs[0]?.size_bytes).toBeGreaterThan(0);
    });
  });

  describe('addToLibrary', () => {
    it('returns document with in_library set to true', async () => {
      const doc = await addToLibrary('11111111-1111-1111-1111-111111111111');
      expect(doc.in_library).toBe(true);
    });
  });
});
