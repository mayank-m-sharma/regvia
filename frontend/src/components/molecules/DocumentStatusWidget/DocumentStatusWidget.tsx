import { cn } from '@/lib/utils';
import type { DocumentStatus } from '@/shared/types/types';

interface DocumentStatusWidgetProps {
  filename: string;
  status: DocumentStatus;
  onRetry?: () => void;
}

const statusConfig = {
  pending: { label: 'Queued', color: 'text-amber-500', dot: 'bg-amber-400 animate-pulse-soft' },
  processing: { label: 'Processing', color: 'text-amber-500', dot: 'bg-amber-400 animate-pulse-soft' },
  ready: { label: 'Ready', color: 'text-emerald-500', dot: 'bg-emerald-400' },
  failed: { label: 'Failed', color: 'text-destructive', dot: 'bg-destructive' },
};

export function DocumentStatusWidget({ filename, status, onRetry }: DocumentStatusWidgetProps) {
  const cfg = statusConfig[status];

  return (
    <div className={cn(
      'glass flex items-center gap-3 rounded-full px-4 py-2',
      'shadow-soft fade-in',
    )}
    >
      <span className={cn('h-2 w-2 rounded-full flex-shrink-0', cfg.dot)} />
      <span className="max-w-[160px] truncate text-xs font-medium text-foreground">{filename}</span>
      <span className={cn('text-xs font-medium', cfg.color)}>{cfg.label}</span>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="text-xs text-muted-foreground underline hover:text-foreground"
        >
          Retry
        </button>
      )}
    </div>
  );
}
