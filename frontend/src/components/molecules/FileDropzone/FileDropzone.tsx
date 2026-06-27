import { useRef, useState } from 'react';
import { cn } from '@/lib/utils';

const MAX_SIZE_BYTES = 50 * 1024 * 1024;

interface FileDropzoneProps {
  onFile: (file: File) => void
  onError: (message: string) => void
  disabled?: boolean
}

export function FileDropzone({ onFile, onError, disabled = false }: FileDropzoneProps) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function validate(file: File): string | null {
    if (file.type !== 'application/pdf') return 'Only PDF files are supported.';
    if (file.size > MAX_SIZE_BYTES) return 'File must be 50 MB or smaller.';
    return null;
  }

  function handleFile(file: File) {
    const err = validate(file);
    if (err) { onError(err); return; }
    onFile(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-label="Upload PDF"
      className={cn(
        'flex flex-col items-center justify-center rounded-lg border-2 border-dashed px-8 py-12 text-center transition-colors',
        dragging ? 'border-primary bg-accent' : 'border-muted-foreground/30 hover:border-primary/60',
        disabled && 'cursor-not-allowed opacity-50',
      )}
      onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={disabled ? undefined : handleDrop}
      onClick={() => { if (!disabled) inputRef.current?.click(); }}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click(); }}
    >
      <svg className="mb-3 h-10 w-10 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
      <p className="text-sm font-medium text-foreground">Drag &amp; drop a PDF here</p>
      <p className="mt-1 text-xs text-muted-foreground">or click to browse — max 50 MB</p>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={handleChange}
        disabled={disabled}
      />
    </div>
  );
}
