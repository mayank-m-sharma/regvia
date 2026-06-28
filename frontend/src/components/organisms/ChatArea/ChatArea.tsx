import {
  useState, useCallback, useRef, useEffect,
} from 'react';
import { cn } from '@/lib/utils';
import { PremiumMessageBubble } from '@/components/molecules/PremiumMessageBubble';
import type { ChatMessage } from '@/features/chat';

interface ChatAreaProps {
  messages: ChatMessage[];
  hasDocument: boolean;
  isDocumentReady: boolean;
  onFile: (file: File) => void;
  onFileError: (msg: string) => void;
  onSend: (text: string) => void;
}

const MAX_SIZE = 50 * 1024 * 1024;

function validate(file: File): string | null {
  if (file.type !== 'application/pdf') return 'Only PDF files are supported.';
  if (file.size > MAX_SIZE) return 'File must be 50 MB or smaller.';
  return null;
}

const SUGGESTIONS = [
  'What are the key obligations in this document?',
  'What are the main compliance risks?',
  'Are there any data retention requirements?',
  'Summarise the key deadlines.',
];

export function ChatArea({
  messages, hasDocument, isDocumentReady, onFile, onFileError, onSend,
}: ChatAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const dragCounter = useRef(0);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleFile = useCallback((file: File) => {
    const err = validate(file);
    if (err) { onFileError(err); return; }
    onFile(file);
  }, [onFile, onFileError]);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    dragCounter.current += 1;
    if (dragCounter.current === 1) setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    dragCounter.current -= 1;
    if (dragCounter.current === 0) setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    dragCounter.current = 0;
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  return (
    <div
      className="relative flex flex-1 flex-col overflow-y-auto"
      onDragEnter={handleDragEnter}
      onDragOver={(e) => e.preventDefault()}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drag-over overlay */}
      {isDragging && (
        <div className={cn(
          'absolute inset-0 z-20 flex flex-col items-center justify-center gap-3',
          'bg-primary/5 backdrop-blur-sm fade-in',
          'border-2 border-dashed border-primary/40 rounded-xl m-4',
        )}
        >
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="hsl(var(--primary))" strokeWidth="1.5">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <p className="text-sm font-medium text-primary">Drop PDF to upload</p>
        </div>
      )}

      <div className="mx-auto w-full max-w-3xl flex-1 px-4 py-6">
        {/* Empty state — no document */}
        {!hasDocument && messages.length === 0 && (
          <div className="flex flex-col items-center justify-center gap-8 py-16 text-center fade-in">
            <div className="space-y-3">
              <div className="flex justify-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="hsl(var(--primary))" strokeWidth="1.5">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                  </svg>
                </div>
              </div>
              <h2 className="text-lg font-semibold text-foreground">RegVia Compliance Copilot</h2>
              <p className="max-w-sm text-sm text-muted-foreground">
                Upload a compliance document to get started.
              </p>
            </div>

            {/* Drop zone */}
            <div className={cn(
              'flex w-full max-w-md flex-col items-center justify-center gap-3 rounded-2xl',
              'border-2 border-dashed border-border/60 bg-card/40 px-6 py-10',
              'transition-colors duration-200',
              isDragging && 'border-primary/60 bg-primary/5',
            )}
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="hsl(var(--primary))" strokeWidth="1.5">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">Drag &amp; drop a PDF here</p>
                <p className="text-xs text-muted-foreground">or use the attachment button below · max 50 MB</p>
              </div>
            </div>
          </div>
        )}

        {/* Document uploaded, waiting for ready */}
        {hasDocument && !isDocumentReady && messages.length === 0 && (
          <div className="flex flex-col items-center justify-center gap-3 py-16 text-center fade-in">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50 dark:bg-amber-950/30">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 6v6l4 2" />
              </svg>
            </div>
            <p className="text-sm font-medium text-foreground">Training your document…</p>
            <p className="max-w-xs text-xs text-muted-foreground">
              This usually takes 30–60 seconds.
              {' '}
              You&apos;ll be able to ask questions once it&apos;s ready.
            </p>
          </div>
        )}

        {/* Document ready, no messages yet */}
        {hasDocument && isDocumentReady && messages.length === 0 && (
          <div className="flex flex-col items-center justify-center gap-4 py-16 text-center fade-in">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 dark:bg-emerald-950/30">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                <path d="M9 11l3 3L22 4" />
                <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
              </svg>
            </div>
            <p className="text-sm font-medium text-foreground">Document ready — ask anything</p>
            <div className="flex max-w-lg flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => onSend(s)}
                  className={cn(
                    'rounded-xl border border-border/60 bg-card/60 px-3 py-2',
                    'text-xs text-muted-foreground',
                    'cursor-pointer transition-colors duration-150',
                    'hover:border-primary/40 hover:bg-primary/5 hover:text-foreground',
                  )}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="space-y-6">
          {messages.map((msg) => (
            <PremiumMessageBubble key={msg.id} message={msg} />
          ))}
        </div>

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
