import { Badge } from '@/components/atoms';
import type { DocumentStatus } from '@/shared/types/types';

const config: Record<DocumentStatus, { label: string; variant: 'default' | 'secondary' | 'warning' | 'success' | 'destructive' }> = {
  pending: { label: 'Pending', variant: 'secondary' },
  processing: { label: 'Processing', variant: 'warning' },
  ready: { label: 'Ready', variant: 'success' },
  failed: { label: 'Failed', variant: 'destructive' },
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  const { label, variant } = config[status];
  return <Badge variant={variant}>{label}</Badge>;
}
