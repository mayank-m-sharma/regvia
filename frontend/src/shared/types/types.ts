import type { z } from 'zod';
import type {
  DocumentSchema,
  DocumentStatusSchema,
  CitationSchema,
  MessageSchema,
  ObligationSchema,
  RiskSchema,
  GapSchema,
  RecommendationSchema,
  SummarySchema,
  ApiErrorSchema,
} from './schemas';

export type DocumentStatus = z.infer<typeof DocumentStatusSchema>;
export type Document = z.infer<typeof DocumentSchema>;
export type Citation = z.infer<typeof CitationSchema>;
export type Message = z.infer<typeof MessageSchema>;
export type Obligation = z.infer<typeof ObligationSchema>;
export type Risk = z.infer<typeof RiskSchema>;
export type Gap = z.infer<typeof GapSchema>;
export type Recommendation = z.infer<typeof RecommendationSchema>;
export type Summary = z.infer<typeof SummarySchema>;
export type ApiError = z.infer<typeof ApiErrorSchema>;
