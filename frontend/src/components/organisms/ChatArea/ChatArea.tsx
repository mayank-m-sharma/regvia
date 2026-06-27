import { useCallback, useRef } from 'react';
import { cn } from '@/lib/utils';
import { PremiumMessageBubble } from '@/components/molecules/PremiumMessageBubble';
import type { ChatMessage } from '@/features/chat';

interface ChatAreaProps {
  messages: ChatMessage[];
  hasDocument: boolean;
  isDocumentReady: boolean;
  isUploading: boolean;
  onFile: (file: File) => void;
  onFileError: (msg: string) => void;
}

const MAX_SIZE = 50 * 1024 * 1024;

function validate(file: File): string | null {
  if (file.type !== 'application/pdf') return 'Only PDF files are supported.';
  if (file.size > MAX_SIZE) return 'File must be 50 MB or smaller.';
  return null;
}

export function ChatArea({
  messages, hasDocument, isDocumentReady, isUploading, onFile, onFileError,
}: ChatAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((file: File) => {
    const err = validate(file);
    if (err) { onFileError(err); return; }
    onFile(file);
  }, [onFile, onFileError]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  // Empty state — no document uploaded yet
  if (!hasDocument) {
    return (
      <div
        className="flex flex-1 flex-col items-center justify-center p-8"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        <div className={cn(
          'flex w-full max-w-lg flex-col items-center gap-6 rounded-2xl p-10 text-center',
          'glass shadow-glass transition-all duration-300',
          isUploading && 'opacity-60',
        )}
        >
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="hsl(var(--primary))" strokeWidth="1.5">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="12" y1="18" x2="12" y2="12" />
              <line x1="9" y1="15" x2="15" y2="15" />
            </svg>
          </div>
          <div className="space-y-2">
            <h2 className="text-xl font-semibold text-foreground">Upload a compliance document</h2>
            <p className="text-sm text-muted-foreground">
              Drop a PDF here or click to browse. We&apos;ll extract obligations,
              risks, and let you ask questions.
            </p>
          </div>
          <button
            type="button"
            disabled={isUploading}
            onClick={() => inputRef.current?.click()}
            className={cn(
              'flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-medium',
              'bg-primary text-primary-foreground shadow-glow',
              'transition-all duration-200 hover:opacity-90 hover:shadow-lg',
              'disabled:cursor-not-allowed disabled:opacity-50',
            )}
          >
            {isUploading ? (
              <>
                <span className="flex gap-1">
                  <span className="typing-dot h-1.5 w-1.5 rounded-full bg-white" />
                  <span className="typing-dot h-1.5 w-1.5 rounded-full bg-white" />
                  <span className="typing-dot h-1.5 w-1.5 rounded-full bg-white" />
                </span>
                Uploading&hellip;
              </>
            ) : (
              <>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
                Choose PDF
              </>
            )}
          </button>
          <p className="text-xs text-muted-foreground/60">Max 50 MB &middot; PDF only</p>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />
      </div>
    );
  }

  // Has document — show messages or waiting state
  return (
    <div className="flex flex-1 flex-col overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl flex-1 space-y-6 px-4 py-6">
        {messages.length === 0 && isDocumentReady && (
          <div className="flex flex-col items-center justify-center gap-3 py-16 text-center fade-in">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="hsl(var(--primary))" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 8v4l3 3" />
              </svg>
            </div>
            <p className="text-sm font-medium text-foreground">Document ready</p>
            <p className="max-w-xs text-xs text-muted-foreground">
              Ask anything about your document &mdash; obligations, risks, definitions, deadlines.
            </p>
          </div>
        )}
        {messages.map((msg) => (
          <PremiumMessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
