import {
  describe, it, expect, beforeEach,
} from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/test/render';
import { useAuthStore } from '@/store/authStore';
import { ProtectedRoute } from './ProtectedRoute';

describe('ProtectedRoute', () => {
  beforeEach(() => {
    useAuthStore.setState({ token: null, user: null });
  });

  it('renders children when token is present', () => {
    useAuthStore.setState({ token: 'valid-token', user: null });
    renderWithProviders(
      <ProtectedRoute>
        <div>protected content</div>
      </ProtectedRoute>,
    );
    expect(screen.getByText('protected content')).toBeInTheDocument();
  });

  it('redirects to / when no token', () => {
    // With MemoryRouter at '/', Navigate to '/' will just stay at '/'
    // We verify children are NOT rendered
    renderWithProviders(
      <ProtectedRoute>
        <div>protected content</div>
      </ProtectedRoute>,
    );
    expect(screen.queryByText('protected content')).not.toBeInTheDocument();
  });
});
