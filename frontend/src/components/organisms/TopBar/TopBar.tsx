import { cn } from '@/lib/utils';

interface TopBarProps {
  dark: boolean;
  setDark: (d: boolean) => void;
  documentName?: string;
  documentReady?: boolean;
  onSummaryClick: () => void;
}

export function TopBar({
  dark, setDark, documentName, documentReady, onSummaryClick,
}: TopBarProps) {
  return (
    <header className={cn(
      'glass z-20 flex h-14 flex-shrink-0 items-center justify-between px-6',
      'border-b border-border/60',
    )}
    >
      <div className="flex items-center gap-3">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary shadow-glow">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
          </svg>
        </div>
        <span className="text-sm font-semibold tracking-tight text-foreground">RegVia</span>
        {documentName && (
          <>
            <span className="text-muted-foreground/40">/</span>
            <span className="max-w-[200px] truncate text-sm text-muted-foreground">{documentName}</span>
          </>
        )}
      </div>

      <div className="flex items-center gap-2">
        {documentReady && (
          <button
            type="button"
            onClick={onSummaryClick}
            className={cn(
              'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium',
              'bg-accent text-accent-foreground transition-all duration-200',
              'hover:bg-primary hover:text-primary-foreground hover:shadow-glow',
            )}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
            </svg>
            Summary
          </button>
        )}
        <button
          type="button"
          onClick={() => setDark(!dark)}
          className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          aria-label="Toggle theme"
        >
          {dark ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="5" />
              <line x1="12" y1="1" x2="12" y2="3" />
              <line x1="12" y1="21" x2="12" y2="23" />
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
              <line x1="1" y1="12" x2="3" y2="12" />
              <line x1="21" y1="12" x2="23" y2="12" />
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
            </svg>
          )}
        </button>
      </div>
    </header>
  );
}
