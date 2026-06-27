import { useParams } from 'react-router-dom';
import { AppLayout } from '@/components/templates/AppLayout';
import { TwoColumnLayout } from '@/components/templates/TwoColumnLayout';
import { MessageList } from '@/components/organisms/MessageList';
import { ChatInputBar } from '@/components/organisms/ChatInputBar';
import { SummaryPanel } from '@/components/organisms/SummaryPanel';
import { useChatSession } from '@/features/chat';
import { useUIStore } from '@/store';
import { cn } from '@/lib/utils';

export function ChatPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const { messages, isStreaming, sendQuestion } = useChatSession(documentId ?? '');
  const { activeTab, setActiveTab } = useUIStore();

  const tabs = ['chat', 'summary'] as const;

  return (
    <AppLayout>
      <TwoColumnLayout
        left={<MessageList messages={messages} />}
        right={(
          <div className="flex h-full flex-col">
            <div className="flex border-b border-border">
              {tabs.map((tab) => (
                <button
                  key={tab}
                  type="button"
                  className={cn(
                    'flex-1 py-2.5 text-sm font-medium capitalize transition-colors',
                    activeTab === tab
                      ? 'border-b-2 border-primary text-foreground'
                      : 'text-muted-foreground hover:text-foreground',
                  )}
                  onClick={() => setActiveTab(tab)}
                >
                  {tab}
                </button>
              ))}
            </div>
            <div className="flex-1 overflow-hidden">
              {activeTab === 'chat'
                ? <ChatInputBar onSend={sendQuestion} disabled={isStreaming} />
                : <SummaryPanel documentId={documentId ?? ''} />}
            </div>
          </div>
        )}
      />
    </AppLayout>
  );
}
