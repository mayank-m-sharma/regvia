import { Spinner } from '@/components/atoms';
import { StatusBadge } from '@/components/molecules/StatusBadge';
import type { DocumentStatus } from '@/shared/types/types';

const descriptions: Record<DocumentStatus, string> = {
  pending: 'Queued for processing…',
  processing: 'Extracting text and generating embeddings…',
  ready: 'Your document is ready.',
  failed: 'Processing failed. Please try uploading again.',
};

export function ProcessingStatus({ status }: { status: DocumentStatus }) {
  return (
    <div className="flex items-center gap-3">
      {(status === 'pending' || status === 'processing') && <Spinner size="sm" />}
      <StatusBadge status={status} />
      <span className="text-sm text-muted-foreground">{descriptions[status]}</span>
    </div>
  );
}
