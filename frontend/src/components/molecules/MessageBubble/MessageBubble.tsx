import { cn } from '@/lib/utils';
import { Spinner } from '@/components/atoms';
import { CitationCard } from '@/components/molecules/CitationCard';
import type { ChatMessage } from '@/features/chat';

interface MessageBubbleProps {
  message: ChatMessage
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={cn('flex flex-col gap-2', isUser ? 'items-end' : 'items-start')}>
      <div
        className={cn(
          'max-w-[80%] rounded-lg px-4 py-2.5 text-sm',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-foreground',
          !message.foundInDocument && !isUser && 'text-muted-foreground italic',
          message.error && 'bg-destructive/10 text-destructive',
        )}
      >
        {message.content || (message.streaming && <Spinner size="sm" />)}
        {message.streaming && message.content && (
          <span className="ml-1 inline-block h-3 w-0.5 animate-pulse bg-current" />
        )}
      </div>

      {!isUser && message.citations.length > 0 && (
        <div className="flex w-full max-w-[80%] flex-col gap-1.5">
          {message.citations.map((c) => (
            <CitationCard key={c.chunk_id} citation={c} />
          ))}
        </div>
      )}
    </div>
  );
}
