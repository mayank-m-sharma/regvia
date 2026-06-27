import { SeverityBadge } from '@/components/atoms/SeverityBadge';
import { PageRef } from '@/components/atoms/PageRef';

interface SummaryItemProps {
  text: string;
  severity?: 'high' | 'medium' | 'low';
  pageNumber?: number | null;
}

export function SummaryItem({ text, severity, pageNumber }: SummaryItemProps) {
  return (
    <div className="flex flex-col gap-1 rounded-md border border-border bg-card p-3">
      <p className="text-sm text-foreground">{text}</p>
      <div className="flex items-center gap-2">
        {severity && <SeverityBadge severity={severity} />}
        <PageRef pageNumber={pageNumber} />
      </div>
    </div>
  );
}
