import { useState } from 'react';
import { Input } from '@/components/atoms/Input';
import { Button } from '@/components/atoms';

interface ChatInputBarProps {
  onSend: (question: string) => void
  disabled?: boolean
}

export function ChatInputBar({ onSend, disabled = false }: ChatInputBarProps) {
  const [value, setValue] = useState('');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setValue('');
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 border-t border-border p-4">
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Ask a question about your document…"
        disabled={disabled}
        className="flex-1"
      />
      <Button type="submit" disabled={disabled || !value.trim()}>
        Send
      </Button>
    </form>
  );
}
