import {
  useState, useCallback, useRef, useEffect,
} from 'react';
import { useNavigate } from 'react-router-dom';
import { TopBar } from '@/components/organisms/TopBar';
import { cn } from '@/lib/utils';
import {
  uploadDocument, getDocuments, addToLibrary,
} from '@/shared/api';
import type { Document } from '@/shared/types/types';

interface KnowledgeLibraryPageProps {
  dark: boolean;
  setDark: (d: boolean) => void;
}

interface UploadItem {
  id: string;
  file: File;
  progress: number;
  status: 'uploading' | 'processing' | 'ready' | 'failed';
  documentId?: string;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Queued',
  processing: 'Training\u2026',
  ready: 'Ready',
  failed: 'Failed',
};

const STATUS_COLOURS: Record<string, string> = {
  pending: 'text-muted-foreground',
  processing: 'text-amber-500',
  ready: 'text-emerald-500',
  failed: 'text-destructive',
};

function UploadStatusText({ status }: { status: UploadItem['status'] }) {
  if (status === 'processing') return <p className="text-xs text-amber-500 mt-0.5">Training\u2026</p>;
  if (status === 'ready') return <p className="text-xs text-emerald-500 mt-0.5">Ready</p>;
  if (status === 'failed') return <p className="text-xs text-destructive mt-0.5">Failed</p>;
  return null;
}

export function KnowledgeLibraryPage({ dark, setDark }: KnowledgeLibraryPageProps) {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadDocuments = useCallback(async () => {
    try {
      const docs = await getDocuments(true);
      setDocuments(docs);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments().catch(() => {});
  }, [loadDocuments]);

  // Poll processing documents every 3s
  useEffect(() => {
    const processingIds = uploads
      .filter((u) => u.status === 'processing' && u.documentId)
      .map((u) => u.documentId!);

    if (processingIds.length === 0) {
      if (pollRef.current) clearInterval(pollRef.current);
      return () => {};
    }

    const doPoll = async () => {
      const fresh = await getDocuments(true);
      setDocuments(fresh);
      setUploads((prev) => prev.map((u) => {
        if (!u.documentId || u.status !== 'processing') return u;
        const doc = fresh.find((d) => d.document_id === u.documentId);
        if (!doc) return u;
        if (doc.status === 'ready' || doc.status === 'failed') {
          return { ...u, status: doc.status };
        }
        return u;
      }));
    };

    pollRef.current = setInterval(() => { doPoll().catch(() => {}); }, 3000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [uploads]);

  function enqueueFiles(files: FileList | File[]) {
    const pdfs = Array.from(files).filter((f) => f.type === 'application/pdf');
    if (pdfs.length === 0) return;

    const newItems: UploadItem[] = pdfs.map((f) => ({
      id: crypto.randomUUID(),
      file: f,
      progress: 0,
      status: 'uploading' as const,
    }));

    setUploads((prev) => [...prev, ...newItems]);

    newItems.forEach((item) => {
      uploadDocument(
        item.file,
        (pct) => {
          setUploads((prev) => prev.map(
            (u) => (u.id === item.id ? { ...u, progress: pct } : u),
          ));
        },
        true,
      )
        .then((doc) => {
          setUploads((prev) => prev.map(
            (u) => (u.id === item.id
              ? {
                ...u,
                progress: 100,
                status: doc.status === 'ready' ? 'ready' : 'processing',
                documentId: doc.document_id,
              }
              : u),
          ));
          setDocuments((prev) => {
            if (prev.find((d) => d.document_id === doc.document_id)) return prev;
            return [doc, ...prev];
          });
        })
        .catch(() => {
          setUploads((prev) => prev.map(
            (u) => (u.id === item.id ? { ...u, status: 'failed' } : u),
          ));
        });
    });
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files) enqueueFiles(e.target.files);
    e.target.value = '';
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files) enqueueFiles(e.dataTransfer.files);
  }

  function handleAddToLibraryClick(documentId: string) {
    addToLibrary(documentId)
      .then((updated) => {
        setDocuments((prev) => prev.map(
          (d) => (d.document_id === documentId ? updated : d),
        ));
      })
      .catch(() => {});
  }

  return (
    <div className={cn('flex h-screen flex-col overflow-hidden', 'bg-gradient-to-br from-background via-background to-accent/10')}>
      <TopBar dark={dark} setDark={setDark} onSummaryClick={() => {}} />

      <div className="flex flex-1 flex-col overflow-hidden p-6 gap-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">Knowledge Library</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Upload documents to your library so you can ask questions across all of them.
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate('/chat')}
            className="text-sm text-primary hover:underline"
          >
            ← Back to chat
          </button>
        </div>

        {/* Drop zone */}
        <div
          className={cn(
            'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors',
            isDragging
              ? 'border-primary bg-primary/5'
              : 'border-border hover:border-primary/50 hover:bg-accent/20',
          )}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') fileInputRef.current?.click(); }}
          aria-label="Upload PDF files to Knowledge Library"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            multiple
            className="hidden"
            onChange={handleFileInput}
          />
          <div className="flex flex-col items-center gap-2">
            <svg className="w-10 h-10 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="text-sm font-medium text-foreground">
              Drop PDF files here or click to browse
            </p>
            <p className="text-xs text-muted-foreground">Multiple files supported · Max 50 MB each</p>
          </div>
        </div>

        {/* Active uploads */}
        {uploads.length > 0 && (
          <div className="space-y-2">
            <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
              Uploading
            </h2>
            {uploads.map((item) => (
              <div
                key={item.id}
                className="flex items-center gap-3 rounded-lg border border-border bg-card p-3"
              >
                <svg className="w-4 h-4 text-muted-foreground shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{item.file.name}</p>
                  {item.status === 'uploading' && (
                    <div className="mt-1 h-1.5 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all"
                        style={{ width: `${item.progress}%` }}
                      />
                    </div>
                  )}
                  <UploadStatusText status={item.status} />
                </div>
                {item.status === 'uploading' && (
                  <span className="text-xs text-muted-foreground">
                    {`${item.progress}%`}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Documents table */}
        <div className="flex-1 overflow-auto">
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">
            Library Documents
          </h2>

          {loading && (
            <div className="flex items-center justify-center py-12">
              <svg className="animate-spin w-6 h-6 text-primary" fill="none" viewBox="0 0 24 24" aria-label="Loading">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            </div>
          )}

          {!loading && documents.length === 0 && (
            <div className="rounded-xl border border-dashed border-border py-12 text-center">
              <p className="text-sm text-muted-foreground">
                No documents in your library yet. Upload some PDFs above to get started.
              </p>
            </div>
          )}

          {!loading && documents.length > 0 && (
            <div className="rounded-xl border border-border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Filename</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Size</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Chunks</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Uploaded</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {documents.map((doc) => (
                    <tr key={doc.document_id} className="hover:bg-muted/20 transition-colors">
                      <td className="px-4 py-3 font-medium truncate max-w-xs">{doc.filename}</td>
                      <td className="px-4 py-3">
                        <span className={cn('font-medium', STATUS_COLOURS[doc.status])}>
                          {STATUS_LABELS[doc.status] ?? doc.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{formatBytes(doc.size_bytes)}</td>
                      <td className="px-4 py-3 text-muted-foreground">{doc.chunk_count ?? '—'}</td>
                      <td className="px-4 py-3 text-muted-foreground">{formatDate(doc.created_at)}</td>
                      <td className="px-4 py-3 flex gap-3">
                        {doc.status === 'ready' && (
                          <button
                            type="button"
                            onClick={() => navigate('/chat')}
                            className="text-primary text-xs hover:underline"
                          >
                            Chat →
                          </button>
                        )}
                        {!doc.in_library && (
                          <button
                            type="button"
                            onClick={() => handleAddToLibraryClick(doc.document_id)}
                            className="text-xs text-muted-foreground hover:text-primary"
                          >
                            + Add to library
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
