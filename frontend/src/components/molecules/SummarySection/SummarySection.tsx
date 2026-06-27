import { Skeleton } from '@/components/atoms/Skeleton';
import { SummaryItem } from '@/components/molecules/SummaryItem';

interface Item {
  text: string;
  severity?: 'high' | 'medium' | 'low';
  page_number?: number | null;
}

interface SummarySectionProps {
  title: string;
  items: Item[];
  isLoading?: boolean;
}

export function SummarySection({ title, items, isLoading = false }: SummarySectionProps) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h3>
      {isLoading ? (
        <>
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-3/4" />
        </>
      ) : (
        items.map((item, i) => (
          <SummaryItem
            // eslint-disable-next-line react/no-array-index-key
            key={i}
            text={item.text}
            severity={item.severity}
            pageNumber={item.page_number}
          />
        ))
      )}
    </div>
  );
}
