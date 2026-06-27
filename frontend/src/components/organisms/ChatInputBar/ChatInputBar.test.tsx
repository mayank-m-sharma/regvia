import {
  describe, it, expect, vi,
} from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/render';
import { ChatInputBar } from './ChatInputBar';

describe('ChatInputBar', () => {
  it('renders input and send button', () => {
    renderWithProviders(<ChatInputBar onSend={vi.fn()} />);
    expect(screen.getByPlaceholderText(/ask a question/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
  });

  it('calls onSend with trimmed text on submit', async () => {
    const onSend = vi.fn();
    renderWithProviders(<ChatInputBar onSend={onSend} />);
    await userEvent.type(screen.getByPlaceholderText(/ask a question/i), 'What are the obligations?');
    await userEvent.click(screen.getByRole('button', { name: /send/i }));
    expect(onSend).toHaveBeenCalledWith('What are the obligations?');
  });

  it('clears input after submit', async () => {
    renderWithProviders(<ChatInputBar onSend={vi.fn()} />);
    const input = screen.getByPlaceholderText(/ask a question/i);
    await userEvent.type(input, 'Hello');
    await userEvent.click(screen.getByRole('button', { name: /send/i }));
    expect(input).toHaveValue('');
  });

  it('does not call onSend when input is empty', async () => {
    const onSend = vi.fn();
    renderWithProviders(<ChatInputBar onSend={onSend} />);
    await userEvent.click(screen.getByRole('button', { name: /send/i }));
    expect(onSend).not.toHaveBeenCalled();
  });

  it('disables input and button when disabled prop passed', () => {
    renderWithProviders(<ChatInputBar onSend={vi.fn()} disabled />);
    expect(screen.getByPlaceholderText(/ask a question/i)).toBeDisabled();
    expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
  });
});
