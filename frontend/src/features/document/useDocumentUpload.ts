import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { uploadDocument } from '@/shared/api';
import type { Document } from '@/shared/types/types';

export function useDocumentUpload(onSuccess: (doc: Document) => void) {
  const [uploadProgress, setUploadProgress] = useState(0);

  const mutation = useMutation({
    mutationFn: (file: File) => uploadDocument(file, setUploadProgress),
    onSuccess,
    onSettled: () => setUploadProgress(0),
  });

  return { ...mutation, uploadProgress };
}
