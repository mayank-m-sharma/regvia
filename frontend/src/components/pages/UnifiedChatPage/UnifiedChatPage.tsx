import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { useDocumentUpload } from '@/features/document/useDocumentUpload';
import { useDocumentStatus } from '@/features/document/useDocumentStatus';
import { useChatSession } from '@/features/chat/useChatSession';
import { createSession, getSession } from '@/shared/api';
import { TopBar } from '@/components/organisms/TopBar';
import { ChatArea } from '@/components/organisms/ChatArea';
import { ChatInputArea } from '@/components/organisms/ChatInputArea';
import { UploadProgressPanel } from '@/components/organisms/UploadProgressPanel';
import { SummarySlideOver } from '@/components/organisms/SummarySlideOver';
import { ChatSidebar } from '@/components/organisms/ChatSidebar';

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
  sessionId: string | null,
  isProcessing: boolean,
  hasFailed: boolean,
): string {
  if (!sessionId) return 'Upload a document to start chatting\u2026';
  if (isProcessing) return 'Document is being processed\u2026';
  if (hasFailed) return 'Processing failed \u2014 retry via the panel below';
  return 'Ask anything about your document\u2026';
}

export function UnifiedChatPage({ dark, setDark }: UnifiedChatPageProps) {
  const { sessionId: routeSessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const [sessionId, setSessionId] = useState<string | null>(routeSessionId ?? null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null);
  const [panelDismissed, setPanelDismissed] = useState(false);
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0);
  const autoDismissRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Track whether we've already created a session for the current upload
  const sessionCreatedRef = useRef(false);

  // Derive documentId from session when sessionId is set
  useEffect(() => {
    if (!sessionId) {
      setDocumentId(null);
      return;
    }
    getSession(sessionId)
      .then((detail) => setDocumentId(detail.document_id))
      .catch(() => {});
  }, [sessionId]);

  // Sync route param on navigation
  useEffect(() => {
    if (routeSessionId !== sessionId) {
      setSessionId(routeSessionId ?? null);
      setUploadedFile(null);
      setPanelDismissed(false);
      sessionCreatedRef.current = false;
    }
  }, [routeSessionId, sessionId]);

  const { data: docStatus } = useDocumentStatus(documentId);
  const { messages, isStreaming, sendQuestion } = useChatSession(sessionId, documentId);

  const upload = useDocumentUpload((doc) => {
    setDocumentId(doc.document_id);
    sessionCreatedRef.current = false;
  });

  // Once document is ready, create a session and navigate to it
  useEffect(() => {
    if (
      docStatus?.status === 'ready'
      && documentId
      && !sessionCreatedRef.current
      && !routeSessionId // don't create for already-loaded sessions
    ) {
      sessionCreatedRef.current = true;
      createSession(documentId)
        .then((s) => {
          setSessionId(s.id);
          setSidebarRefreshKey((k) => k + 1);
          navigate(`/chat/${s.id}`, { replace: true });
        })
        .catch(() => {});
    }
  }, [docStatus?.status, documentId, routeSessionId, navigate]);

  // Auto-dismiss panel 3s after document is ready
  useEffect(() => {
    if (docStatus?.status === 'ready' && uploadedFile && !panelDismissed) {
      autoDismissRef.current = setTimeout(() => setPanelDismissed(true), 3000);
    }
    return () => {
      if (autoDismissRef.current) clearTimeout(autoDismissRef.current);
    };
  }, [docStatus?.status, uploadedFile, panelDismissed]);

  // Refresh sidebar after a message is sent (to update last_message_at order)
  const lastMsgCount = messages.length;
  const prevMsgCountRef = useRef(0);
  useEffect(() => {
    if (lastMsgCount > prevMsgCountRef.current && !isStreaming) {
      setSidebarRefreshKey((k) => k + 1);
    }
    prevMsgCountRef.current = lastMsgCount;
  }, [lastMsgCount, isStreaming]);

  function handleFile(file: File) {
    setPanelDismissed(false);
    setUploadedFile({ name: file.name, size: file.size, type: file.type });
    upload.mutate(file);
  }

  function handleRetry() {
    setDocumentId(null);
    setSessionId(null);
    setUploadedFile(null);
    setPanelDismissed(false);
    sessionCreatedRef.current = false;
    upload.reset();
    navigate('/chat', { replace: true });
  }

  function handleNewChat() {
    setDocumentId(null);
    setSessionId(null);
    setUploadedFile(null);
    setPanelDismissed(false);
    sessionCreatedRef.current = false;
    upload.reset();
    navigate('/chat', { replace: true });
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

      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar */}
        <ChatSidebar
          activeSessionId={sessionId}
          onNewChat={handleNewChat}
          refreshKey={sidebarRefreshKey}
        />

        {/* Main chat column */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <ChatArea
            messages={messages}
            hasDocument={!!sessionId}
            isDocumentReady={isReady}
            onFile={handleFile}
            onFileError={() => {}}
            onSend={sendQuestion}
          />

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
            placeholder={getPlaceholder(sessionId, isProcessing, hasFailed)}
            showAttachment={!sessionId}
          />
        </div>
      </div>

      {summaryOpen && documentId && (
        <SummarySlideOver
          documentId={documentId}
          onClose={() => setSummaryOpen(false)}
        />
      )}
    </div>
  );
}
