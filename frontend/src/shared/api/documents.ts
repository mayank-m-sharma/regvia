import { z } from 'zod';
import apiClient from './client';
import { ApiValidationError } from './errors';
import { ApiResponseSchema, DocumentSchema } from '@/shared/types/schemas';
import type { Document } from '@/shared/types/types';

const DocumentResponseSchema = ApiResponseSchema(DocumentSchema);
const DocumentListResponseSchema = ApiResponseSchema(z.array(DocumentSchema));

export async function uploadDocument(
  file: File,
  onProgress?: (pct: number) => void,
  inLibrary = false,
): Promise<Document> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<z.infer<typeof DocumentResponseSchema>>(
    `/documents?in_library=${inLibrary}`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
    },
  );

  const parsed = DocumentResponseSchema.safeParse(response.data);
  if (!parsed.success) {
    throw new ApiValidationError(`Invalid document response: ${parsed.error.message}`);
  }

  return parsed.data.data;
}

export async function getDocumentStatus(id: string): Promise<Document> {
  const response = await apiClient.get<z.infer<typeof DocumentResponseSchema>>(`/documents/${id}`);

  const parsed = DocumentResponseSchema.safeParse(response.data);
  if (!parsed.success) {
    throw new ApiValidationError(`Invalid document status response: ${parsed.error.message}`);
  }

  return parsed.data.data;
}

export async function getDocuments(inLibrary?: boolean): Promise<Document[]> {
  const params = inLibrary !== undefined ? `?in_library=${inLibrary}` : '';
  const response = await apiClient.get<z.infer<typeof DocumentListResponseSchema>>(
    `/documents${params}`,
  );

  const parsed = DocumentListResponseSchema.safeParse(response.data);
  if (!parsed.success) {
    throw new ApiValidationError(`Invalid documents list response: ${parsed.error.message}`);
  }

  return parsed.data.data;
}

export async function addToLibrary(documentId: string): Promise<Document> {
  const response = await apiClient.patch<z.infer<typeof DocumentResponseSchema>>(
    `/documents/${documentId}/library`,
  );

  const parsed = DocumentResponseSchema.safeParse(response.data);
  if (!parsed.success) {
    throw new ApiValidationError(`Invalid add-to-library response: ${parsed.error.message}`);
  }

  return parsed.data.data;
}
