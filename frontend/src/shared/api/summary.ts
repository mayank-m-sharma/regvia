import { z } from 'zod';
import apiClient from './client';
import { ApiValidationError } from './errors';
import { ApiResponseSchema, SummarySchema } from '@/shared/types/schemas';
import type { Summary } from '@/shared/types/types';

const SummaryResponseSchema = ApiResponseSchema(SummarySchema);

// eslint-disable-next-line import/prefer-default-export
export async function getSummary(documentId: string): Promise<Summary> {
  const response = await apiClient.post<z.infer<typeof SummaryResponseSchema>>(
    `/documents/${documentId}/summary`,
  );

  const parsed = SummaryResponseSchema.safeParse(response.data);
  if (!parsed.success) {
    throw new ApiValidationError(`Invalid summary response: ${parsed.error.message}`);
  }

  return parsed.data.data;
}
