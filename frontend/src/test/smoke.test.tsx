import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from './render';

describe('test infrastructure smoke test', () => {
  it('renders a basic element', () => {
    renderWithProviders(<div>hello</div>);
    expect(screen.getByText('hello')).toBeInTheDocument();
  });

  it('custom render wraps providers without crashing', () => {
    renderWithProviders(<p data-testid="probe">works</p>);
    expect(screen.getByTestId('probe')).toBeInTheDocument();
  });
});
