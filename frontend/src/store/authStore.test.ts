import {
  describe, it, expect, beforeEach,
} from 'vitest';
import { useAuthStore } from './authStore';

describe('authStore', () => {
  beforeEach(() => {
    useAuthStore.setState({ token: null, user: null });
  });

  it('starts with no token or user', () => {
    const { token, user } = useAuthStore.getState();
    expect(token).toBeNull();
    expect(user).toBeNull();
  });

  it('setToken stores the token', () => {
    useAuthStore.getState().setToken('test-jwt');
    expect(useAuthStore.getState().token).toBe('test-jwt');
  });

  it('setUser stores the user', () => {
    const user = {
      id: '1', email: 'a@b.com', displayName: 'Test', avatarUrl: null,
    };
    useAuthStore.getState().setUser(user);
    expect(useAuthStore.getState().user).toEqual(user);
  });

  it('logout clears token and user', () => {
    useAuthStore.getState().setToken('tok');
    useAuthStore.getState().setUser({
      id: '1', email: 'a@b.com', displayName: null, avatarUrl: null,
    });
    useAuthStore.getState().logout();
    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().user).toBeNull();
  });
});
