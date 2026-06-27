import { Button } from '@/components/atoms';
import { SummarySection } from '@/components/molecules/SummarySection';
import { useSummary } from '@/features/summary';

interface SummaryPanelProps {
  documentId: string;
}

export function SummaryPanel({ documentId }: SummaryPanelProps) {
  const {
    summary, isLoading, isError, generate,
  } = useSummary(documentId);

  if (!summary && !isLoading) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 p-6">
        <p className="text-center text-sm text-muted-foreground">
          Generate a structured compliance summary with obligations, risks, gaps,
          and recommendations.
        </p>
        <Button onClick={() => generate()}>
          Generate Summary
        </Button>
        {isError && (
          <p role="alert" className="text-sm text-destructive">
            Failed to generate summary. Please try again.
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 overflow-y-auto p-4">
      <SummarySection
        title="Obligations"
        items={summary?.obligations ?? []}
        isLoading={isLoading}
      />
      <SummarySection
        title="Risks"
        items={(summary?.risks ?? []).map((r) => ({ ...r, severity: r.severity }))}
        isLoading={isLoading}
      />
      <SummarySection
        title="Gaps"
        items={summary?.gaps ?? []}
        isLoading={isLoading}
      />
      <SummarySection
        title="Recommendations"
        items={(summary?.recommendations ?? []).map((r) => ({ ...r, severity: r.priority }))}
        isLoading={isLoading}
      />
    </div>
  );
}
