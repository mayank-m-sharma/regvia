import { truncateText } from '@/shared/utils';
import type { Citation } from '@/shared/types/types';

interface CitationCardProps {
  citation: Citation
}

export function CitationCard({ citation }: CitationCardProps) {
  return (
    <div className="rounded-md border border-border bg-muted/40 px-3 py-2 text-xs">
      <span className="font-medium text-muted-foreground">
        {`p.${citation.page_number}`}
      </span>
      <p className="mt-0.5 text-foreground/80 italic">
        {`"${truncateText(citation.excerpt, 120)}"`}
      </p>
    </div>
  );
}
