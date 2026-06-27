import { useState } from 'react';
import { cn } from '@/lib/utils';

interface ChatInputAreaProps {
  onSend: (q: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInputArea({ onSend, disabled = false, placeholder }: ChatInputAreaProps) {
  const [value, setValue] = useState('');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  }

  return (
    <div className="flex-shrink-0 px-4 pb-4 pt-2">
      <div className="mx-auto max-w-3xl">
        <form
          onSubmit={handleSubmit}
          className={cn(
            'glass-strong flex items-end gap-3 rounded-2xl px-4 py-3 shadow-soft-lg',
            'transition-all duration-200',
            !disabled && 'focus-within:shadow-glow focus-within:ring-1 focus-within:ring-primary/30',
          )}
        >
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder ?? 'Ask anything about your document\u2026'}
            disabled={disabled}
            rows={1}
            className={cn(
              'flex-1 resize-none bg-transparent text-sm text-foreground outline-none',
              'placeholder:text-muted-foreground/60',
              'disabled:cursor-not-allowed disabled:opacity-50',
              'max-h-32 overflow-y-auto',
            )}
            style={{ lineHeight: '1.5' }}
          />
          <button
            type="submit"
            disabled={disabled || !value.trim()}
            className={cn(
              'flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl',
              'bg-primary text-primary-foreground',
              'transition-all duration-200 hover:opacity-90',
              'disabled:cursor-not-allowed disabled:opacity-30',
            )}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="12" y1="19" x2="12" y2="5" />
              <polyline points="5 12 12 5 19 12" />
            </svg>
          </button>
        </form>
        <p className="mt-1.5 text-center text-xs text-muted-foreground/50">
          Shift+Enter for new line &middot; Enter to send
        </p>
      </div>
    </div>
  );
}
