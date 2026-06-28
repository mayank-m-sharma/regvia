import { useState, useRef } from 'react';
import { cn } from '@/lib/utils';

interface ChatInputAreaProps {
  onSend: (q: string) => void;
  onFile: (file: File) => void;
  disabled?: boolean;
  sendDisabled?: boolean;
  placeholder?: string;
  showAttachment?: boolean;
}

const MAX_SIZE = 50 * 1024 * 1024;

export function ChatInputArea({
  onSend, onFile, disabled = false, sendDisabled = false, placeholder, showAttachment = true,
}: ChatInputAreaProps) {
  const [value, setValue] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled || sendDisabled) return;
    onSend(trimmed);
    setValue('');
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.type !== 'application/pdf' || file.size > MAX_SIZE) return;
    onFile(file);
    // reset so same file can be re-selected
    e.target.value = '';
  }

  const canSend = !disabled && !sendDisabled && value.trim().length > 0;

  return (
    <div className="flex-shrink-0 px-4 pb-4 pt-2">
      <div className="mx-auto max-w-3xl">
        <form
          onSubmit={handleSubmit}
          className={cn(
            'glass-strong flex items-end gap-2 rounded-2xl px-3 py-3 shadow-soft-lg',
            'transition-all duration-200',
            !disabled && 'focus-within:shadow-glow focus-within:ring-1 focus-within:ring-primary/30',
          )}
        >
          {/* Attachment button — only before a document is loaded */}
          {showAttachment && (
            <>
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                disabled={disabled}
                className={cn(
                  'flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl',
                  'text-muted-foreground transition-colors duration-200',
                  'hover:bg-secondary hover:text-foreground',
                  'disabled:cursor-not-allowed disabled:opacity-40',
                )}
                aria-label="Attach PDF"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
                </svg>
              </button>
              <input
                ref={fileRef}
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={handleFileChange}
              />
            </>
          )}

          {/* Textarea */}
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

          {/* Send */}
          <button
            type="submit"
            disabled={!canSend}
            className={cn(
              'flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl',
              'bg-primary text-primary-foreground',
              'transition-all duration-200 hover:opacity-90',
              'disabled:cursor-not-allowed disabled:opacity-30',
            )}
            aria-label="Send"
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
