import { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { useSummary } from '@/features/summary';
import { Skeleton } from '@/components/atoms/Skeleton';

const severityColors = {
  high: 'bg-destructive/10 text-destructive border-destructive/20',
  medium: [
    'bg-amber-50 text-amber-700 border-amber-200',
    'dark:bg-amber-950/30 dark:text-amber-400 dark:border-amber-800/40',
  ].join(' '),
  low: [
    'bg-emerald-50 text-emerald-700 border-emerald-200',
    'dark:bg-emerald-950/30 dark:text-emerald-400 dark:border-emerald-800/40',
  ].join(' '),
};

function Section({
  title, color, children,
}: {
  title: string;
  color: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <h3 className={cn('text-xs font-semibold uppercase tracking-widest', color)}>{title}</h3>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function ItemCard({
  text, pageNumber, severity,
}: {
  text: string;
  pageNumber?: number | null;
  severity?: 'high' | 'medium' | 'low';
}) {
  return (
    <div className={cn(
      'rounded-xl border border-border/60 bg-card/60 p-3 text-sm',
      'space-y-2 transition-colors hover:bg-card',
    )}
    >
      <p className="text-foreground/90 leading-relaxed">{text}</p>
      <div className="flex items-center gap-2">
        {severity && (
          <span className={cn(
            'rounded-md border px-2 py-0.5 text-xs font-medium capitalize',
            severityColors[severity],
          )}
          >
            {severity}
          </span>
        )}
        {pageNumber != null && (
          <span className="text-xs text-muted-foreground">{`p.${pageNumber}`}</span>
        )}
      </div>
    </div>
  );
}

interface SummarySlideOverProps {
  documentId: string;
  onClose: () => void;
}

export function SummarySlideOver({ documentId, onClose }: SummarySlideOverProps) {
  const {
    summary, isLoading, isError, generate,
  } = useSummary(documentId);

  useEffect(() => {
    if (!summary && !isLoading) generate();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-30 bg-foreground/10 backdrop-blur-sm fade-in"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div className={cn(
        'fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col',
        'glass-strong shadow-glass-dark slide-in-right',
        'border-l border-border/60',
      )}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/60 px-6 py-4">
          <div>
            <h2 className="text-sm font-semibold text-foreground">Compliance Summary</h2>
            <p className="text-xs text-muted-foreground">AI-generated overview</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className={cn(
              'rounded-lg p-1.5 text-muted-foreground transition-colors',
              'hover:bg-secondary hover:text-foreground',
            )}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {isError && (
            <div className="rounded-xl bg-destructive/10 p-4 text-sm text-destructive">
              Failed to generate summary. Please try again.
            </div>
          )}

          {isLoading && (
            <>
              {['Obligations', 'Risks', 'Gaps', 'Recommendations'].map((s) => (
                <div key={s} className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                    {s}
                  </p>
                  <Skeleton className="h-16 w-full shimmer" />
                  <Skeleton className="h-16 w-3/4 shimmer" />
                </div>
              ))}
            </>
          )}

          {summary && (
            <>
              <Section title="Obligations" color="text-blue-600 dark:text-blue-400">
                {summary.obligations.map((o, i) => (
                  // eslint-disable-next-line react/no-array-index-key
                  <ItemCard key={i} text={o.text} pageNumber={o.page_number} />
                ))}
              </Section>

              <Section title="Risks" color="text-destructive">
                {/* eslint-disable react/no-array-index-key */}
                {summary.risks.map((r, i) => (
                  <ItemCard
                    key={i}
                    text={r.text}
                    pageNumber={r.page_number}
                    severity={r.severity}
                  />
                ))}
                {/* eslint-enable react/no-array-index-key */}
              </Section>

              <Section title="Gaps" color="text-amber-600 dark:text-amber-400">
                {summary.gaps.map((g, i) => (
                  // eslint-disable-next-line react/no-array-index-key
                  <ItemCard key={i} text={g.text} pageNumber={g.page_number} />
                ))}
              </Section>

              <Section title="Recommendations" color="text-emerald-600 dark:text-emerald-400">
                {summary.recommendations.map((r, i) => (
                  // eslint-disable-next-line react/no-array-index-key
                  <ItemCard key={i} text={r.text} severity={r.priority} />
                ))}
              </Section>
            </>
          )}
        </div>
      </div>
    </>
  );
}
