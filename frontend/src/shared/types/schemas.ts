import { z } from 'zod';

export const DocumentStatusSchema = z.enum(['pending', 'processing', 'ready', 'failed']);

export const DocumentSchema = z.object({
  document_id: z.string().uuid(),
  filename: z.string(),
  status: DocumentStatusSchema,
  chunk_count: z.number().nullish(),
  size_bytes: z.number().int(),
  in_library: z.boolean(),
  created_at: z.string().datetime({ offset: true }),
  updated_at: z.string().datetime({ offset: true }),
});

export const CitationSchema = z.object({
  chunk_id: z.string().uuid(),
  page_number: z.number(),
  excerpt: z.string(),
});

export const MessageSchema = z.object({
  session_id: z.string().uuid(),
  message_id: z.string().uuid(),
  answer: z.string(),
  citations: z.array(CitationSchema),
  found_in_document: z.boolean(),
});

export const ObligationSchema = z.object({
  text: z.string(),
  page_number: z.number().nullable(),
  chunk_id: z.string().uuid().nullable(),
});

export const RiskSchema = z.object({
  text: z.string(),
  severity: z.enum(['high', 'medium', 'low']),
  page_number: z.number().nullable(),
  chunk_id: z.string().uuid().nullable(),
});

export const GapSchema = z.object({
  text: z.string(),
  page_number: z.number().nullable(),
  chunk_id: z.string().uuid().nullable(),
});

export const RecommendationSchema = z.object({
  text: z.string(),
  priority: z.enum(['high', 'medium', 'low']),
});

export const SummarySchema = z.object({
  document_id: z.string().uuid(),
  obligations: z.array(ObligationSchema),
  risks: z.array(RiskSchema),
  gaps: z.array(GapSchema),
  recommendations: z.array(RecommendationSchema),
  generated_at: z.string().datetime({ offset: true }),
});

export const ChatSessionSchema = z.object({
  id: z.string().uuid(),
  document_id: z.string().uuid().nullable(), // null for library sessions
  document_filename: z.string().nullable(),
  title: z.string().nullable(),
  created_at: z.string().datetime({ offset: true }),
  last_message_at: z.string().datetime({ offset: true }).nullable(),
  message_count: z.number().int(),
});

export const ChatHistoryMessageSchema = z.object({
  id: z.string().uuid(),
  role: z.enum(['user', 'assistant']),
  content: z.string(),
  citations: z.array(CitationSchema),
  created_at: z.string().datetime({ offset: true }),
});

export const ChatSessionDetailSchema = z.object({
  id: z.string().uuid(),
  document_id: z.string().uuid().nullable(), // null for library sessions
  document_filename: z.string().nullable(),
  title: z.string().nullable(),
  created_at: z.string().datetime({ offset: true }),
  last_message_at: z.string().datetime({ offset: true }).nullable(),
  messages: z.array(ChatHistoryMessageSchema),
});

export const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  display_name: z.string().nullable(),
  avatar_url: z.string().nullable(),
});

export const ApiErrorSchema = z.object({
  message: z.string(),
  code: z.string(),
});

export const ApiResponseSchema = <T extends z.ZodTypeAny>(dataSchema: T) => z.object({
  data: dataSchema,
  error: z.union([z.null(), ApiErrorSchema]),
});
