import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { useDocumentUpload } from '@/features/document/useDocumentUpload';
import { useDocumentStatus } from '@/features/document/useDocumentStatus';
import { useChatSession } from '@/features/chat/useChatSession';
import { TopBar } from '@/components/organisms/TopBar';
import { ChatArea } from '@/components/organisms/ChatArea';
import { ChatInputArea } from '@/components/organisms/ChatInputArea';
import { DocumentStatusWidget } from '@/components/molecules/DocumentStatusWidget';
import { SummarySlideOver } from '@/components/organisms/SummarySlideOver';

interface UnifiedChatPageProps {
  dark: boolean;
  setDark: (d: boolean) => void;
}

function getPlaceholder(
  documentId: string | null,
  isProcessing: boolean,
  hasFailed: boolean,
): string {
  if (!documentId) return 'Upload a document to get started\u2026';
  if (isProcessing) return 'Processing document\u2026';
  if (hasFailed) return 'Processing failed \u2014 please retry';
  return 'Ask anything about your document\u2026';
}

export function UnifiedChatPage({ dark, setDark }: UnifiedChatPageProps) {
  const { documentId: routeDocId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const [documentId, setDocumentId] = useState<string | null>(routeDocId ?? null);
  const [summaryOpen, setSummaryOpen] = useState(false);

  const { data: docStatus } = useDocumentStatus(documentId);
  const { messages, isStreaming, sendQuestion } = useChatSession(documentId ?? '');

  const upload = useDocumentUpload((doc) => {
    setDocumentId(doc.document_id);
    navigate(`/chat/${doc.document_id}`, { replace: true });
  });

  // Sync route param if navigating directly
  useEffect(() => {
    if (routeDocId && routeDocId !== documentId) {
      setDocumentId(routeDocId);
    }
  }, [routeDocId, documentId]);

  const isReady = docStatus?.status === 'ready';
  const isProcessing = !!documentId && docStatus?.status !== 'ready' && docStatus?.status !== 'failed';
  const hasFailed = docStatus?.status === 'failed';

  return (
    <div className={cn(
      'flex h-screen flex-col overflow-hidden',
      'bg-gradient-to-br from-background via-background to-accent/10',
    )}
    >
      <TopBar
        dark={dark}
        setDark={setDark}
        documentName={docStatus?.filename}
        documentReady={isReady}
        onSummaryClick={() => setSummaryOpen(true)}
      />

      <div className="relative flex flex-1 overflow-hidden">
        {/* Document status widget — floats above chat */}
        {documentId && docStatus && !isReady && (
          <div className="absolute left-1/2 top-4 z-10 -translate-x-1/2">
            <DocumentStatusWidget
              filename={docStatus.filename}
              status={docStatus.status}
              onRetry={hasFailed ? () => { setDocumentId(null); upload.reset(); } : undefined}
            />
          </div>
        )}

        <ChatArea
          messages={messages}
          hasDocument={!!documentId}
          isDocumentReady={isReady}
          isUploading={upload.isPending}
          onFile={(file) => upload.mutate(file)}
          onFileError={() => {}}
        />
      </div>

      <ChatInputArea
        onSend={sendQuestion}
        disabled={isStreaming || !isReady}
        placeholder={getPlaceholder(documentId, isProcessing, hasFailed)}
      />

      {summaryOpen && documentId && (
        <SummarySlideOver
          documentId={documentId}
          onClose={() => setSummaryOpen(false)}
        />
      )}
    </div>
  );
}
