import { useState } from 'react';
import Markdown from 'react-markdown';
import { cn } from '@/lib/utils';
import { truncateText } from '@/shared/utils';
import type { ChatMessage } from '@/features/chat';

/** Strip `[chunk:uuid]` markers and `[Source ...]` inline references from streamed text. */
function cleanContent(raw: string): string {
  return raw
    // Remove chunk ID markers: [chunk:uuid]
    .replace(/\[chunk:[a-f0-9-]+\]/gi, '')
    // Remove bracketed source references: [Source of ... ]
    .replace(/\[Source[^\]]*\]/gi, '')
    // Remove any remaining bare bracketed UUIDs
    .replace(/\[[a-f0-9-]{36}\]/g, '')
    // Collapse multiple blank lines left behind
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-1 py-2">
      <span className="typing-dot h-2 w-2 rounded-full bg-muted-foreground/60" />
      <span className="typing-dot h-2 w-2 rounded-full bg-muted-foreground/60" />
      <span className="typing-dot h-2 w-2 rounded-full bg-muted-foreground/60" />
    </div>
  );
}

interface CitationBubblesProps {
  citations: ChatMessage['citations'];
}

function CitationBubbles({ citations }: CitationBubblesProps) {
  const [expanded, setExpanded] = useState(false);

  if (citations.length === 0) return null;

  return (
    <div className="mt-3 space-y-2">
      {/* Inline source bubbles */}
      <div className="flex flex-wrap gap-1.5">
        {citations.map((c, i) => (
          <button
            key={c.chunk_id}
            type="button"
            onClick={() => setExpanded((prev) => !prev)}
            className={cn(
              'inline-flex items-center gap-1 rounded-full px-2.5 py-1',
              'bg-primary/10 text-xs font-medium text-primary',
              'border border-primary/20 transition-all duration-150',
              'hover:bg-primary/20 hover:border-primary/40',
            )}
          >
            <span className={cn(
              'flex h-4 w-4 items-center justify-center rounded-full',
              'bg-primary/20 text-[10px] font-semibold',
            )}
            >
              {c.page_number ?? i + 1}
            </span>
            p.
            {c.page_number ?? i + 1}
          </button>
        ))}
        <button
          type="button"
          onClick={() => setExpanded((prev) => !prev)}
          className={cn(
            'inline-flex items-center gap-1 rounded-full px-2.5 py-1',
            'text-xs text-muted-foreground transition-colors hover:text-foreground',
          )}
        >
          {expanded ? 'Hide excerpts' : 'Show excerpts'}
          <svg
            width="10"
            height="10"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            className={cn('transition-transform duration-200', expanded && 'rotate-180')}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
      </div>

      {/* Expanded excerpts */}
      {expanded && (
        <div className="flex flex-col gap-2 fade-in">
          {citations.map((c) => (
            <div
              key={c.chunk_id}
              className={cn(
                'flex gap-3 rounded-xl p-3',
                'bg-accent/50 transition-colors hover:bg-accent',
              )}
            >
              <div className={cn(
                'flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-md',
                'bg-primary/10 text-xs font-semibold text-primary',
              )}
              >
                {c.page_number}
              </div>
              <p className="text-xs leading-relaxed text-muted-foreground italic">
                &ldquo;
                {truncateText(c.excerpt, 160)}
                &rdquo;
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface PremiumMessageBubbleProps {
  message: ChatMessage;
}

export function PremiumMessageBubble({ message }: PremiumMessageBubbleProps) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end fade-in">
        <div className={cn(
          'max-w-[70%] rounded-2xl rounded-tr-sm px-4 py-3 text-sm',
          'bg-primary text-primary-foreground shadow-soft',
        )}
        >
          {message.content}
        </div>
      </div>
    );
  }

  const displayContent = cleanContent(message.content);

  return (
    <div className="flex gap-3 fade-in">
      <div className={cn(
        'flex h-7 w-7 flex-shrink-0 items-center justify-center',
        'rounded-lg bg-primary/10 mt-0.5',
      )}
      >
        <svg
          width="13"
          height="13"
          viewBox="0 0 24 24"
          fill="none"
          stroke="hsl(var(--primary))"
          strokeWidth="2"
        >
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
        </svg>
      </div>
      <div className="flex-1 min-w-0">
        <div className={cn(
          'text-sm leading-relaxed',
          message.error && 'text-destructive',
        )}
        >
          {message.streaming && !message.content ? (
            <TypingIndicator />
          ) : (
            <>
              <div className={cn(
                'prose prose-sm max-w-none',
                'prose-headings:font-semibold prose-headings:text-foreground',
                'prose-p:text-foreground prose-p:leading-relaxed prose-p:my-1',
                'prose-strong:text-foreground prose-strong:font-semibold',
                'prose-ul:text-foreground prose-ol:text-foreground',
                'prose-li:text-foreground prose-li:my-0.5',
                'prose-code:text-primary prose-code:bg-accent/50',
                'prose-code:rounded prose-code:px-1 prose-code:py-0.5 prose-code:text-xs',
                'prose-blockquote:text-muted-foreground prose-blockquote:border-primary/40',
                !message.foundInDocument && 'prose-p:text-muted-foreground prose-p:italic',
                message.error && 'prose-p:text-destructive',
              )}
              >
                <Markdown>{displayContent}</Markdown>
              </div>
              {message.streaming && (
                <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-primary align-middle" />
              )}
            </>
          )}
        </div>
        {!message.streaming && !message.error && (
          <CitationBubbles citations={message.citations} />
        )}
      </div>
    </div>
  );
}
