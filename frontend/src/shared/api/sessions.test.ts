import { describe, it, expect } from 'vitest';
import { getSessions, createSession, getSession } from './sessions';

const SESSION_ID = '55555555-5555-5555-5555-555555555555';

describe('sessions API', () => {
  describe('getSessions', () => {
    it('returns list of sessions including library sessions', async () => {
      const sessions = await getSessions();
      expect(sessions).toHaveLength(2);
      expect(sessions[0]?.title).toBe('Data Retention Policy');
      expect(sessions[0]?.message_count).toBe(4);
      // Library session has null document_id
      expect(sessions[1]?.document_id).toBeNull();
    });
  });

  describe('createSession', () => {
    it('returns the created session', async () => {
      const session = await createSession('11111111-1111-1111-1111-111111111111');
      expect(session.id).toBe(SESSION_ID);
      expect(session.message_count).toBe(0);
      expect(session.title).toBeNull();
    });
  });

  describe('getSession', () => {
    it('returns session with messages', async () => {
      const detail = await getSession(SESSION_ID);
      expect(detail.id).toBe(SESSION_ID);
      expect(detail.messages).toHaveLength(2);
      expect(detail.messages[0]?.role).toBe('user');
      expect(detail.messages[1]?.role).toBe('assistant');
    });

    it('includes document filename', async () => {
      const detail = await getSession(SESSION_ID);
      expect(detail.document_filename).toBe('test.pdf');
    });
  });
});
