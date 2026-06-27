import { useMutation } from '@tanstack/react-query';
import { uploadDocument } from '@/shared/api';
import type { Document } from '@/shared/types/types';

export function useDocumentUpload(onSuccess: (doc: Document) => void) {
  return useMutation({
    mutationFn: (file: File) => uploadDocument(file),
    onSuccess,
  });
}
