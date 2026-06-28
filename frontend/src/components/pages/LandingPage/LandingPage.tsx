import { useState } from 'react';
import { cn } from '@/lib/utils';
import { getLoginUrl } from '@/shared/api';

interface LandingPageProps {
  dark: boolean;
  setDark: (d: boolean) => void;
}

export function LandingPage({ dark, setDark }: LandingPageProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSignIn() {
    setIsLoading(true);
    setError(null);
    try {
      const { url, state } = await getLoginUrl();
      sessionStorage.setItem('oauth_state', state);
      window.location.href = url;
    } catch {
      setError('Failed to initiate sign in. Please try again.');
      setIsLoading(false);
    }
  }

  return (
    <div className={cn(
      'flex h-screen flex-col overflow-hidden',
      'bg-gradient-to-br from-background via-background to-accent/10',
    )}
    >
      {/* Top bar */}
      <header className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="hsl(var(--primary))" strokeWidth="1.5">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <span className="text-sm font-semibold text-foreground">RegVia</span>
        </div>
        <button
          type="button"
          onClick={() => setDark(!dark)}
          className="rounded-md p-2 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
          aria-label="Toggle dark mode"
        >
          {dark ? (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="5" />
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
            </svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
          )}
        </button>
      </header>

      {/* Hero */}
      <main className="flex flex-1 flex-col items-center justify-center px-4 text-center">
        <div className="mx-auto max-w-2xl space-y-8 fade-in">
          {/* Icon */}
          <div className="flex justify-center">
            <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-primary/10 shadow-soft">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="hsl(var(--primary))" strokeWidth="1.5">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
              </svg>
            </div>
          </div>

          {/* Headline */}
          <div className="space-y-3">
            <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
              RegVia Compliance Copilot
            </h1>
            <p className="mx-auto max-w-lg text-lg text-muted-foreground">
              Upload compliance documents and get instant, AI-powered answers.
              Understand obligations, risks, and deadlines in seconds.
            </p>
          </div>

          {/* Feature pills */}
          <div className="flex flex-wrap justify-center gap-2">
            {['PDF analysis', 'RAG-powered Q&A', 'Obligation extraction', 'Risk identification'].map((f) => (
              <span
                key={f}
                className="rounded-full border border-border/60 bg-card/60 px-3 py-1 text-xs text-muted-foreground"
              >
                {f}
              </span>
            ))}
          </div>

          {/* Sign in button */}
          <div className="flex flex-col items-center gap-3">
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
            <button
              type="button"
              onClick={() => { handleSignIn().catch(() => {}); }}
              disabled={isLoading}
              className={cn(
                'glass-strong flex items-center gap-3 rounded-2xl px-6 py-3',
                'text-sm font-medium text-foreground shadow-soft',
                'transition-all duration-200 hover:shadow-soft-lg hover:scale-[1.02]',
                'disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:scale-100',
                'border border-border/60',
              )}
            >
              {isLoading ? (
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                /* Google G logo */
                <svg width="18" height="18" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
              )}
              {isLoading ? 'Redirecting…' : 'Sign in with Google'}
            </button>
            <p className="text-xs text-muted-foreground/60">
              By signing in, you agree to our terms of service.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
