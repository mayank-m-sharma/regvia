import { useParams } from 'react-router-dom';
import { AppLayout } from '@/components/templates/AppLayout';
import { TwoColumnLayout } from '@/components/templates/TwoColumnLayout';
import { MessageList } from '@/components/organisms/MessageList';
import { ChatInputBar } from '@/components/organisms/ChatInputBar';
import { useChatSession } from '@/features/chat';

export function ChatPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const { messages, isStreaming, sendQuestion } = useChatSession(documentId ?? '');

  return (
    <AppLayout>
      <TwoColumnLayout
        left={<MessageList messages={messages} />}
        right={
          <ChatInputBar onSend={sendQuestion} disabled={isStreaming} />
        }
      />
    </AppLayout>
  );
}
