interface PageRefProps {
  pageNumber: number | null | undefined;
}

export function PageRef({ pageNumber }: PageRefProps) {
  if (pageNumber == null) return null;
  return (
    <span className="inline-flex items-center rounded bg-muted px-1.5 py-0.5 text-xs font-medium text-muted-foreground">
      {`p.${pageNumber}`}
    </span>
  );
}
