import {
  useState, useEffect, useRef, useCallback,
} from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { useDocumentUpload } from '@/features/document/useDocumentUpload';
import { useDocumentStatus } from '@/features/document/useDocumentStatus';
import { useChatSession } from '@/features/chat/useChatSession';
import {
  createSession, getSession, addToLibrary,
} from '@/shared/api';
import { TopBar } from '@/components/organisms/TopBar';
import { ChatArea } from '@/components/organisms/ChatArea';
import { ChatInputArea } from '@/components/organisms/ChatInputArea';
import { UploadProgressPanel } from '@/components/organisms/UploadProgressPanel';
import { SummarySlideOver } from '@/components/organisms/SummarySlideOver';
import { ChatSidebar } from '@/components/organisms/ChatSidebar';
import type { Document } from '@/shared/types/types';

type ChatMode = 'document' | 'library';

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
  mode: ChatMode,
  sessionId: string | null,
  isProcessing: boolean,
  hasFailed: boolean,
): string {
  if (mode === 'library') return 'Ask anything across your Knowledge Library…';
  if (!sessionId) return 'Upload a document to start chatting…';
  if (isProcessing) return 'Document is being processed…';
  if (hasFailed) return 'Processing failed — retry via the panel below';
  return 'Ask anything about your document…';
}

export function UnifiedChatPage({ dark, setDark }: UnifiedChatPageProps) {
  const { sessionId: routeSessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const [chatMode, setChatMode] = useState<ChatMode>('document');
  const [sessionId, setSessionId] = useState<string | null>(routeSessionId ?? null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null);
  const [panelDismissed, setPanelDismissed] = useState(false);
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0);
  const [addToLibraryDoc, setAddToLibraryDoc] = useState<Document | null>(null);
  const autoDismissRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sessionCreatedRef = useRef(false);
  // Holds a question to send once sessionId is set (library first-message flow)
  const pendingQuestionRef = useRef<string | null>(null);

  // Derive documentId from session when sessionId is set
  useEffect(() => {
    if (!sessionId) {
      setDocumentId(null);
      return;
    }
    getSession(sessionId)
      .then((detail) => {
        setDocumentId(detail.document_id ?? null);
        setChatMode(detail.document_id ? 'document' : 'library');
      })
      .catch(() => {});
  }, [sessionId]);

  // Sync route param on navigation
  useEffect(() => {
    if (routeSessionId !== sessionId) {
      setSessionId(routeSessionId ?? null);
      setUploadedFile(null);
      setPanelDismissed(false);
      setAddToLibraryDoc(null);
      sessionCreatedRef.current = false;
    }
  }, [routeSessionId, sessionId]);

  const { data: docStatus } = useDocumentStatus(documentId);
  const { messages, isStreaming, sendQuestion } = useChatSession(sessionId, documentId);

  // Fire a pending first question once sessionId and sendQuestion are both updated
  useEffect(() => {
    if (sessionId && pendingQuestionRef.current) {
      const q = pendingQuestionRef.current;
      pendingQuestionRef.current = null;
      sendQuestion(q);
    }
  }, [sessionId, sendQuestion]);

  const upload = useDocumentUpload((doc) => {
    setDocumentId(doc.document_id);
    sessionCreatedRef.current = false;
    if (!doc.in_library) {
      setAddToLibraryDoc(doc);
    }
  });

  // Once document is ready, create a session and navigate to it
  useEffect(() => {
    if (
      chatMode === 'document'
      && docStatus?.status === 'ready'
      && documentId
      && !sessionCreatedRef.current
      && !routeSessionId
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
  }, [chatMode, docStatus?.status, documentId, routeSessionId, navigate]);

  // Auto-dismiss panel 3s after document is ready
  useEffect(() => {
    if (docStatus?.status === 'ready' && uploadedFile && !panelDismissed) {
      autoDismissRef.current = setTimeout(() => setPanelDismissed(true), 3000);
    }
    return () => {
      if (autoDismissRef.current) clearTimeout(autoDismissRef.current);
    };
  }, [docStatus?.status, uploadedFile, panelDismissed]);

  // Refresh sidebar after a message completes
  const lastMsgCount = messages.length;
  const prevMsgCountRef = useRef(0);
  useEffect(() => {
    if (lastMsgCount > prevMsgCountRef.current && !isStreaming) {
      setSidebarRefreshKey((k) => k + 1);
    }
    prevMsgCountRef.current = lastMsgCount;
  }, [lastMsgCount, isStreaming]);

  // Library mode: create a session on first question, then send
  const handleLibrarySend = useCallback(async (question: string) => {
    if (isStreaming) return;
    if (!sessionId) {
      // Store the question; the effect above will fire it once sessionId updates
      pendingQuestionRef.current = question;
      try {
        const s = await createSession(null);
        setSessionId(s.id);
        setSidebarRefreshKey((k) => k + 1);
        navigate(`/chat/${s.id}`, { replace: true });
      } catch {
        pendingQuestionRef.current = null;
      }
    } else {
      sendQuestion(question);
    }
  }, [isStreaming, sessionId, sendQuestion, navigate]);

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
    setAddToLibraryDoc(null);
    sessionCreatedRef.current = false;
    upload.reset();
    navigate('/chat', { replace: true });
  }

  function handleNewChat() {
    setDocumentId(null);
    setSessionId(null);
    setUploadedFile(null);
    setPanelDismissed(false);
    setAddToLibraryDoc(null);
    sessionCreatedRef.current = false;
    upload.reset();
    navigate('/chat', { replace: true });
  }

  function switchMode(mode: ChatMode) {
    if (mode === chatMode) return;
    setChatMode(mode);
    handleNewChat();
  }

  function handleConfirmAddToLibrary() {
    if (!addToLibraryDoc) return;
    const docId = addToLibraryDoc.document_id;
    setAddToLibraryDoc(null);
    addToLibrary(docId).catch(() => {});
  }

  const isReady = docStatus?.status === 'ready';
  const isProcessing = !!documentId && docStatus?.status !== 'ready' && docStatus?.status !== 'failed';
  const hasFailed = docStatus?.status === 'failed';
  const showPanel = !!uploadedFile && !panelDismissed;

  const sendDisabled = chatMode === 'document'
    ? (isStreaming || !isReady)
    : isStreaming;

  return (
    <div className={cn(
      'flex h-screen flex-col overflow-hidden',
      'bg-gradient-to-br from-background via-background to-accent/10',
    )}
    >
      <TopBar
        dark={dark}
        setDark={setDark}
        documentName={chatMode === 'document' ? docStatus?.filename : 'Knowledge Library'}
        documentReady={chatMode === 'document' ? isReady : true}
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
          {/* Mode toggle */}
          <div className="flex flex-col gap-1 border-b border-border px-4 py-2 bg-background/60">
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => switchMode('document')}
                className={cn(
                  'rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                  chatMode === 'document'
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                Document Chat
              </button>
              <button
                type="button"
                onClick={() => switchMode('library')}
                className={cn(
                  'rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                  chatMode === 'library'
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                Knowledge Library
              </button>
              {chatMode === 'library' && (
                <button
                  type="button"
                  onClick={() => navigate('/library')}
                  className="ml-auto text-xs text-primary hover:underline"
                >
                  Manage library →
                </button>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              {chatMode === 'document'
                ? 'Chat with a single PDF — get precise answers with page citations'
                : 'Search across all documents you\'ve added to your library at once'}
            </p>
          </div>

          {/* Add-to-library prompt */}
          {addToLibraryDoc && (
            <div className="flex items-center justify-between gap-3 border-b border-amber-500/30 bg-amber-500/10 px-4 py-2 text-sm">
              <span className="text-foreground">
                <strong>{addToLibraryDoc.filename}</strong>
                {' is not in your Knowledge Library. Add it so you can ask questions across all your documents?'}
              </span>
              <div className="flex gap-2 shrink-0">
                <button
                  type="button"
                  onClick={handleConfirmAddToLibrary}
                  className="rounded px-2.5 py-1 bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90"
                >
                  Add to Library
                </button>
                <button
                  type="button"
                  onClick={() => setAddToLibraryDoc(null)}
                  className="rounded px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground"
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}

          <ChatArea
            messages={messages}
            hasDocument={chatMode === 'library' || !!sessionId}
            isDocumentReady={chatMode === 'library' || isReady}
            onFile={chatMode === 'document' ? handleFile : () => {}}
            onFileError={() => {}}
            onSend={chatMode === 'library' ? handleLibrarySend : sendQuestion}
            mode={chatMode}
            onManageLibrary={() => navigate('/library')}
          />

          {showPanel && uploadedFile && chatMode === 'document' && (
            <UploadProgressPanel
              file={uploadedFile}
              uploadProgress={upload.isPending ? upload.uploadProgress : 100}
              trainingStatus={docStatus?.status ?? null}
              onRetry={hasFailed ? handleRetry : undefined}
              onDismiss={() => setPanelDismissed(true)}
            />
          )}

          <ChatInputArea
            onSend={chatMode === 'library' ? handleLibrarySend : sendQuestion}
            onFile={chatMode === 'document' ? handleFile : () => {}}
            disabled={false}
            sendDisabled={sendDisabled}
            placeholder={getPlaceholder(chatMode, sessionId, isProcessing, hasFailed)}
            showAttachment={chatMode === 'document' && !sessionId}
          />
        </div>
      </div>

      {summaryOpen && documentId && chatMode === 'document' && (
        <SummarySlideOver
          documentId={documentId}
          onClose={() => setSummaryOpen(false)}
        />
      )}
    </div>
  );
}
