import { z } from 'zod';
import apiClient from './client';
import {
  ApiResponseSchema,
  ChatSessionSchema,
  ChatSessionDetailSchema,
} from '@/shared/types/schemas';

const SessionListSchema = ApiResponseSchema(z.array(ChatSessionSchema));
const SessionCreateSchema = ApiResponseSchema(ChatSessionSchema);
const SessionDetailSchema = ApiResponseSchema(ChatSessionDetailSchema);

export type ChatSession = z.infer<typeof ChatSessionSchema>;
export type ChatSessionDetail = z.infer<typeof ChatSessionDetailSchema>;
export type ChatHistoryMessage = z.infer<typeof ChatSessionDetailSchema>['messages'][number];

export async function getSessions(): Promise<ChatSession[]> {
  const response = await apiClient.get<z.infer<typeof SessionListSchema>>('/chat/sessions');
  // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
  const parsed = SessionListSchema.safeParse(response.data);
  if (!parsed.success || parsed.data.data === undefined) return [];
  return parsed.data.data;
}

export async function createSession(documentId: string | null): Promise<ChatSession> {
  const response = await apiClient.post<z.infer<typeof SessionCreateSchema>>(
    '/chat/sessions',
    { document_id: documentId },
  );
  // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
  const parsed = SessionCreateSchema.safeParse(response.data);
  if (!parsed.success || !parsed.data.data) throw new Error('Invalid session response');
  return parsed.data.data;
}

export async function getSession(sessionId: string): Promise<ChatSessionDetail> {
  const response = await apiClient.get<z.infer<typeof SessionDetailSchema>>(
    `/chat/sessions/${sessionId}`,
  );
  // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
  const parsed = SessionDetailSchema.safeParse(response.data);
  if (!parsed.success || !parsed.data.data) throw new Error('Invalid session detail response');
  return parsed.data.data;
}
