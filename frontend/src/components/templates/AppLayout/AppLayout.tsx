interface AppLayoutProps {
  children: React.ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border px-6 py-4">
        <span className="text-lg font-semibold text-foreground">RegVia — Compliance Copilot</span>
      </header>
      <main className="px-6 py-10">{children}</main>
    </div>
  );
}
