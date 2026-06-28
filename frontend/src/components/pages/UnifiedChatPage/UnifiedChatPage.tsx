import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { useDocumentUpload } from '@/features/document/useDocumentUpload';
import { useDocumentStatus } from '@/features/document/useDocumentStatus';
import { useChatSession } from '@/features/chat/useChatSession';
import { TopBar } from '@/components/organisms/TopBar';
import { ChatArea } from '@/components/organisms/ChatArea';
import { ChatInputArea } from '@/components/organisms/ChatInputArea';
import { UploadProgressPanel } from '@/components/organisms/UploadProgressPanel';
import { SummarySlideOver } from '@/components/organisms/SummarySlideOver';

interface UploadedFile {
  name: string;
  size: number;
  type: string;
}

interface UnifiedChatPageProps {
  dark: boolean;
  setDark: (d: boolean) => void;
}

function getPlaceholder(
  documentId: string | null,
  isProcessing: boolean,
  hasFailed: boolean,
): string {
  if (!documentId) return 'Upload a document via the paperclip, then ask questions\u2026';
  if (isProcessing) return 'Document is being processed\u2026';
  if (hasFailed) return 'Processing failed \u2014 retry via the panel below';
  return 'Ask anything about your document\u2026';
}

export function UnifiedChatPage({ dark, setDark }: UnifiedChatPageProps) {
  const { documentId: routeDocId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const [documentId, setDocumentId] = useState<string | null>(routeDocId ?? null);
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null);
  const [panelDismissed, setPanelDismissed] = useState(false);
  const autoDismissRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { data: docStatus } = useDocumentStatus(documentId);
  const { messages, isStreaming, sendQuestion } = useChatSession(documentId ?? '');

  const upload = useDocumentUpload((doc) => {
    setDocumentId(doc.document_id);
    navigate(`/chat/${doc.document_id}`, { replace: true });
  });

  // Sync route param when navigating directly to /chat/:id
  useEffect(() => {
    if (routeDocId && routeDocId !== documentId) {
      setDocumentId(routeDocId);
    }
  }, [routeDocId, documentId]);

  // Auto-dismiss the panel 3s after document becomes ready
  useEffect(() => {
    if (docStatus?.status === 'ready' && uploadedFile && !panelDismissed) {
      autoDismissRef.current = setTimeout(() => setPanelDismissed(true), 3000);
    }
    return () => {
      if (autoDismissRef.current) clearTimeout(autoDismissRef.current);
    };
  }, [docStatus?.status, uploadedFile, panelDismissed]);

  function handleFile(file: File) {
    setPanelDismissed(false);
    setUploadedFile({ name: file.name, size: file.size, type: file.type });
    upload.mutate(file);
  }

  function handleRetry() {
    setDocumentId(null);
    setUploadedFile(null);
    setPanelDismissed(false);
    upload.reset();
    navigate('/', { replace: true });
  }

  const isReady = docStatus?.status === 'ready';
  const isProcessing = !!documentId && docStatus?.status !== 'ready' && docStatus?.status !== 'failed';
  const hasFailed = docStatus?.status === 'failed';

  const showPanel = !!uploadedFile && !panelDismissed;

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

      <ChatArea
        messages={messages}
        hasDocument={!!documentId}
        isDocumentReady={isReady}
        onFile={handleFile}
        onFileError={() => {}}
        onSend={sendQuestion}
      />

      {/* Upload progress panel — sits between chat and input */}
      {showPanel && uploadedFile && (
        <UploadProgressPanel
          file={uploadedFile}
          uploadProgress={upload.isPending ? upload.uploadProgress : 100}
          trainingStatus={docStatus?.status ?? null}
          onRetry={hasFailed ? handleRetry : undefined}
          onDismiss={() => setPanelDismissed(true)}
        />
      )}

      <ChatInputArea
        onSend={sendQuestion}
        onFile={handleFile}
        disabled={false}
        sendDisabled={isStreaming || !isReady}
        placeholder={getPlaceholder(documentId, isProcessing, hasFailed)}
        showAttachment={!documentId}
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
