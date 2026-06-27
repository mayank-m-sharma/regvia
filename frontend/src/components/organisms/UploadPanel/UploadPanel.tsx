import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileDropzone } from '@/components/molecules/FileDropzone';
import { ProcessingStatus } from '@/components/molecules/ProcessingStatus';
import { Button } from '@/components/atoms';
import { useDocumentUpload } from '@/features/document/useDocumentUpload';
import { useDocumentStatus } from '@/features/document/useDocumentStatus';
import type { Document } from '@/shared/types/types';

export function UploadPanel() {
  const navigate = useNavigate();
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const { data: docStatus } = useDocumentStatus(documentId);

  // Navigate to chat when ready
  if (docStatus?.status === 'ready') {
    navigate(`/chat/${docStatus.document_id}`);
  }

  const upload = useDocumentUpload((doc: Document) => {
    setDocumentId(doc.document_id);
  });

  function handleRetry() {
    setDocumentId(null);
    upload.reset();
  }

  return (
    <div className="mx-auto w-full max-w-lg space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Upload a compliance document</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload a PDF to start asking questions and generating compliance summaries.
        </p>
      </div>

      {!documentId && (
        <>
          <FileDropzone
            onFile={(file) => {
              setValidationError(null);
              upload.mutate(file);
            }}
            onError={setValidationError}
            disabled={upload.isPending}
          />
          {validationError && (
            <p role="alert" className="text-sm text-destructive">{validationError}</p>
          )}
          {upload.isError && (
            <p role="alert" className="text-sm text-destructive">
              Upload failed. Please try again.
            </p>
          )}
        </>
      )}

      {documentId && docStatus && (
        <div className="space-y-4">
          <ProcessingStatus status={docStatus.status} />
          {docStatus.status === 'failed' && (
            <Button variant="outline" onClick={handleRetry}>
              Try again
            </Button>
          )}
        </div>
      )}

      {documentId && !docStatus && (
        <ProcessingStatus status="pending" />
      )}
    </div>
  );
}
