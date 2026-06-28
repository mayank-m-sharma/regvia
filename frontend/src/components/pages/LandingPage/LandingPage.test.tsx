import {
  describe, it, expect, vi, beforeEach,
} from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/test/render';
import { LandingPage } from './LandingPage';

const mockGetLoginUrl = vi.fn();

vi.mock('@/shared/api', () => ({
  // eslint-disable-next-line @typescript-eslint/no-unsafe-return
  getLoginUrl: () => mockGetLoginUrl(),
}));

describe('LandingPage', () => {
  const noop = () => {};

  beforeEach(() => {
    mockGetLoginUrl.mockReset();
  });

  it('renders the sign in button', () => {
    renderWithProviders(<LandingPage dark={false} setDark={noop} />);
    expect(screen.getByText(/sign in with google/i)).toBeInTheDocument();
  });

  it('renders the product name', () => {
    renderWithProviders(<LandingPage dark={false} setDark={noop} />);
    expect(screen.getByText(/regvia compliance copilot/i)).toBeInTheDocument();
  });

  it('clicking sign in calls getLoginUrl', async () => {
    mockGetLoginUrl.mockResolvedValue('https://accounts.google.com/auth');
    Object.defineProperty(window, 'location', {
      value: { href: '' },
      writable: true,
    });

    renderWithProviders(<LandingPage dark={false} setDark={noop} />);
    fireEvent.click(screen.getByText(/sign in with google/i));

    await waitFor(() => {
      expect(mockGetLoginUrl).toHaveBeenCalledOnce();
    });
  });

  it('shows error when getLoginUrl fails', async () => {
    mockGetLoginUrl.mockRejectedValue(new Error('Network error'));

    renderWithProviders(<LandingPage dark={false} setDark={noop} />);
    fireEvent.click(screen.getByText(/sign in with google/i));

    await waitFor(() => {
      expect(screen.getByText(/failed to initiate sign in/i)).toBeInTheDocument();
    });
  });

  it('toggles dark mode on button click', () => {
    const setDark = vi.fn();
    renderWithProviders(<LandingPage dark={false} setDark={setDark} />);
    fireEvent.click(screen.getByLabelText(/toggle dark mode/i));
    expect(setDark).toHaveBeenCalledWith(true);
  });
});
