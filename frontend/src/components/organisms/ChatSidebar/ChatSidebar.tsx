import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { getSessions } from '@/shared/api';
import type { ChatSession } from '@/shared/api';

interface ChatSidebarProps {
  activeSessionId: string | null;
  onNewChat: () => void;
  /** Increment to trigger a session list refresh */
  refreshKey?: number;
}

function timeAgo(iso: string | null): string {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function ChatSidebar({ activeSessionId, onNewChat, refreshKey = 0 }: ChatSidebarProps) {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getSessions()
      .then(setSessions)
      .catch(() => setSessions([]))
      .finally(() => setLoading(false));
  }, [refreshKey]);

  return (
    <aside
      className={cn(
        'flex h-full w-64 flex-shrink-0 flex-col',
        'border-r border-border/60 bg-card/40 backdrop-blur-sm',
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/40 px-4 py-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Chats
        </span>
        <button
          type="button"
          onClick={onNewChat}
          title="New chat"
          className={cn(
            'flex h-7 w-7 items-center justify-center rounded-lg',
            'text-muted-foreground transition-colors',
            'hover:bg-primary/10 hover:text-primary',
          )}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto py-2">
        {loading && (
          <div className="flex items-center justify-center py-8">
            <svg className="h-4 w-4 animate-spin text-muted-foreground" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
        )}

        {!loading && sessions.length === 0 && (
          <p className="px-4 py-6 text-center text-xs text-muted-foreground">
            No chats yet. Upload a document to get started.
          </p>
        )}

        {!loading && sessions.map((s) => {
          const isActive = s.id === activeSessionId;
          const label = s.title ?? s.document_filename ?? 'Untitled chat';
          const subtitle = s.document_filename && s.title ? s.document_filename : null;
          const time = timeAgo(s.last_message_at ?? s.created_at);

          return (
            <button
              key={s.id}
              type="button"
              onClick={() => navigate(`/chat/${s.id}`)}
              className={cn(
                'w-full px-3 py-2.5 text-left transition-colors',
                isActive
                  ? 'bg-primary/10 text-foreground'
                  : 'text-muted-foreground hover:bg-secondary/60 hover:text-foreground',
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <span className="flex-1 truncate text-xs font-medium leading-tight">
                  {label}
                </span>
                <span className="flex-shrink-0 text-[10px] text-muted-foreground/60">
                  {time}
                </span>
              </div>
              {subtitle && (
                <span className="mt-0.5 block truncate text-[10px] text-muted-foreground/60">
                  {subtitle}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </aside>
  );
}
