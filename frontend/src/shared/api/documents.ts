import { z } from 'zod';
import apiClient from './client';
import { ApiValidationError } from './errors';
import { ApiResponseSchema, DocumentSchema } from '@/shared/types/schemas';
import type { Document } from '@/shared/types/types';

const DocumentResponseSchema = ApiResponseSchema(DocumentSchema);

export async function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<z.infer<typeof DocumentResponseSchema>>(
    '/documents',
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
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
