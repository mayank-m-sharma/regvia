import {
  describe, it, expect, vi, beforeEach,
} from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/test/render';
import { useAuthStore } from '@/store/authStore';
import { AuthCallbackPage } from './AuthCallbackPage';

const mockExchangeCode = vi.fn();
const mockGetMe = vi.fn();
const mockNavigate = vi.fn();

vi.mock('@/shared/api', () => ({
  // eslint-disable-next-line @typescript-eslint/no-unsafe-return
  exchangeCode: (code: string) => mockExchangeCode(code),
  // eslint-disable-next-line @typescript-eslint/no-unsafe-return
  getMe: () => mockGetMe(),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

const VALID_STATE = 'test-oauth-state-abc123';

describe('AuthCallbackPage', () => {
  beforeEach(() => {
    useAuthStore.setState({ token: null, user: null });
    mockExchangeCode.mockReset();
    mockGetMe.mockReset();
    mockNavigate.mockReset();
    sessionStorage.clear();
  });

  it('redirects to / when no code in URL', async () => {
    sessionStorage.setItem('oauth_state', VALID_STATE);
    renderWithProviders(<AuthCallbackPage />, {
      initialEntries: ['/auth/callback'],
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });

  it('redirects to / when state does not match sessionStorage', async () => {
    sessionStorage.setItem('oauth_state', 'different-state');
    renderWithProviders(<AuthCallbackPage />, {
      initialEntries: [`/auth/callback?code=auth-code&state=${VALID_STATE}`],
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });

  it('redirects to / when sessionStorage has no state', async () => {
    renderWithProviders(<AuthCallbackPage />, {
      initialEntries: [`/auth/callback?code=auth-code&state=${VALID_STATE}`],
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });

  it('shows spinner while processing', () => {
    sessionStorage.setItem('oauth_state', VALID_STATE);
    mockExchangeCode.mockReturnValue(new Promise(() => {})); // never resolves

    renderWithProviders(<AuthCallbackPage />, {
      initialEntries: [`/auth/callback?code=auth-code&state=${VALID_STATE}`],
    });

    expect(screen.getByText(/signing you in/i)).toBeInTheDocument();
  });

  it('navigates to /chat on success', async () => {
    sessionStorage.setItem('oauth_state', VALID_STATE);
    mockExchangeCode.mockResolvedValue('valid-jwt');
    mockGetMe.mockResolvedValue({
      id: 'user-1',
      email: 'user@test.com',
      display_name: 'User',
      avatar_url: null,
    });

    renderWithProviders(<AuthCallbackPage />, {
      initialEntries: [`/auth/callback?code=auth-code&state=${VALID_STATE}`],
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/chat', { replace: true });
    });
    expect(useAuthStore.getState().token).toBe('valid-jwt');
    expect(sessionStorage.getItem('oauth_state')).toBeNull();
  });

  it('redirects to / when exchangeCode fails', async () => {
    sessionStorage.setItem('oauth_state', VALID_STATE);
    mockExchangeCode.mockRejectedValue(new Error('exchange failed'));

    renderWithProviders(<AuthCallbackPage />, {
      initialEntries: [`/auth/callback?code=auth-code&state=${VALID_STATE}`],
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });

  it('redirects to / when getMe fails', async () => {
    sessionStorage.setItem('oauth_state', VALID_STATE);
    mockExchangeCode.mockResolvedValue('some-token');
    mockGetMe.mockRejectedValue(new Error('401'));

    renderWithProviders(<AuthCallbackPage />, {
      initialEntries: [`/auth/callback?code=auth-code&state=${VALID_STATE}`],
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });
});
