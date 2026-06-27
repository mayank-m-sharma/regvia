import type React from 'react';

interface TwoColumnLayoutProps {
  left: React.ReactNode
  right: React.ReactNode
}

export function TwoColumnLayout({ left, right }: TwoColumnLayoutProps) {
  return (
    <div className="flex h-[calc(100vh-57px)]">
      <div className="flex flex-1 flex-col overflow-y-auto">{left}</div>
      <div className="flex w-80 flex-shrink-0 flex-col border-l border-border">{right}</div>
    </div>
  );
}
