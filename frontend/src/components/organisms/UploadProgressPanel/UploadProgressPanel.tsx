import { useState } from 'react';
import { cn } from '@/lib/utils';
import type { DocumentStatus } from '@/shared/types/types';

interface UploadFile {
  name: string;
  size: number;
  type: string;
}

interface UploadProgressPanelProps {
  file: UploadFile;
  uploadProgress: number; // 0–100; 100 means upload done, training starting
  trainingStatus: DocumentStatus | null;
  onRetry?: () => void;
  onDismiss: () => void;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const trainingLabels: Record<DocumentStatus, string> = {
  pending: 'Queued for training…',
  processing: 'Training in progress…',
  ready: 'Training complete',
  failed: 'Error in training',
};

const trainingColors: Record<DocumentStatus, string> = {
  pending: 'text-amber-500',
  processing: 'text-amber-500',
  ready: 'text-emerald-500',
  failed: 'text-destructive',
};

export function UploadProgressPanel({
  file, uploadProgress, trainingStatus, onRetry, onDismiss,
}: UploadProgressPanelProps) {
  const [collapsed, setCollapsed] = useState(false);

  const isUploading = uploadProgress < 100;
  const isReady = trainingStatus === 'ready';
  const isFailed = trainingStatus === 'failed';
  const isTraining = !isReady && !isFailed && !isUploading;
  let barColor = 'bg-primary';
  if (isReady) barColor = 'bg-emerald-500';
  else if (isFailed) barColor = 'bg-destructive';

  // Overall progress: first 50% is upload, second 50% is training
  function getOverallProgress(): number {
    if (isUploading) return Math.round(uploadProgress * 0.5);
    if (trainingStatus === 'ready') return 100;
    if (trainingStatus === 'processing') return 75;
    if (trainingStatus === 'pending') return 55;
    return 50;
  }
  const overallProgress = getOverallProgress();

  return (
    <div className={cn(
      'mx-auto w-full max-w-3xl px-4 pb-2',
    )}
    >
      <div className={cn(
        'glass rounded-xl shadow-soft overflow-hidden',
        'border border-border/60 transition-all duration-200',
      )}
      >
        {/* Header row — always visible */}
        <div className="flex items-center gap-3 px-4 py-2.5">
          {/* File type icon */}
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-red-50 dark:bg-red-950/30">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          </div>

          {/* File info */}
          <div className="flex min-w-0 flex-1 flex-col">
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-xs font-medium text-foreground">{file.name}</span>
              <span className="flex-shrink-0 text-xs text-muted-foreground">
                {isUploading && `${uploadProgress}%`}
                {!isUploading && trainingStatus && trainingLabels[trainingStatus]}
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground/70">
              <span>{formatBytes(file.size)}</span>
              <span>·</span>
              <span>PDF</span>
              {trainingStatus && !isUploading && (
                <>
                  <span>·</span>
                  <span className={trainingColors[trainingStatus]}>
                    {isFailed && 'Failed'}
                    {isReady && 'Ready'}
                    {!isFailed && !isReady && 'Training…'}
                  </span>
                </>
              )}
            </div>
          </div>

          {/* Controls */}
          <div className="flex flex-shrink-0 items-center gap-1">
            {isFailed && onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="rounded-md px-2 py-1 text-xs font-medium text-destructive hover:bg-destructive/10 transition-colors"
              >
                Retry
              </button>
            )}
            <button
              type="button"
              onClick={() => setCollapsed(!collapsed)}
              className="rounded-md p-1 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
              aria-label={collapsed ? 'Expand' : 'Collapse'}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className={cn('transition-transform duration-200', collapsed && 'rotate-180')}
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>
            {(isReady || isFailed) && (
              <button
                type="button"
                onClick={onDismiss}
                className="rounded-md p-1 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                aria-label="Dismiss"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* Progress bar — always visible unless collapsed */}
        {!collapsed && (
          <div className="px-4 pb-3">
            <div className="h-1 w-full overflow-hidden rounded-full bg-secondary">
              <div
                className={cn(
                  'h-full rounded-full transition-all duration-500',
                  barColor,
                  isTraining && 'shimmer',
                )}
                style={{ width: `${overallProgress}%` }}
              />
            </div>

            {/* Detail rows */}
            <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground/60">
              <span className={cn(
                uploadProgress === 100 ? 'text-emerald-500' : 'text-muted-foreground/60',
              )}
              >
                {uploadProgress === 100 ? '✓ Uploaded' : `Uploading ${uploadProgress}%`}
              </span>
              {trainingStatus && (
                <span className={trainingColors[trainingStatus]}>
                  {trainingLabels[trainingStatus]}
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
