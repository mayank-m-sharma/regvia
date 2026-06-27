import { z } from 'zod';
import apiClient from './client';
import { ApiValidationError } from './errors';
import { ApiResponseSchema, MessageSchema } from '@/shared/types/schemas';
import type { Message } from '@/shared/types/types';

const MessageResponseSchema = ApiResponseSchema(MessageSchema);

export interface ChatRequest {
  document_id: string;
  session_id: string | null;
  question: string;
}

export async function sendMessage(req: ChatRequest): Promise<Message> {
  const response = await apiClient.post<z.infer<typeof MessageResponseSchema>>('/chat', req);

  const parsed = MessageResponseSchema.safeParse(response.data);
  if (!parsed.success) {
    throw new ApiValidationError(`Invalid chat response: ${parsed.error.message}`);
  }

  return parsed.data.data;
}
