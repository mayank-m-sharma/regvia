import { z } from 'zod';
import apiClient from './client';
import { ApiResponseSchema, UserSchema } from '@/shared/types/schemas';

const LoginUrlSchema = ApiResponseSchema(
  z.object({ url: z.string(), state: z.string() }),
);
const ExchangeSchema = ApiResponseSchema(z.object({ token: z.string() }));
const MeSchema = ApiResponseSchema(UserSchema);

export async function getLoginUrl(): Promise<{ url: string; state: string }> {
  const response = await apiClient.get<z.infer<typeof LoginUrlSchema>>('/auth/login');
  // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
  const parsed = LoginUrlSchema.safeParse(response.data);
  if (!parsed.success || !parsed.data.data) throw new Error('Invalid login URL response');
  return parsed.data.data;
}

export async function exchangeCode(code: string): Promise<string> {
  const response = await apiClient.post<z.infer<typeof ExchangeSchema>>(
    '/auth/exchange',
    { code },
  );
  // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
  const parsed = ExchangeSchema.safeParse(response.data);
  if (!parsed.success || !parsed.data.data) throw new Error('Invalid exchange response');
  return parsed.data.data.token;
}

export async function getMe(): Promise<z.infer<typeof UserSchema>> {
  const response = await apiClient.get<z.infer<typeof MeSchema>>('/auth/me');
  // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
  const parsed = MeSchema.safeParse(response.data);
  if (!parsed.success || !parsed.data.data) throw new Error('Invalid /me response');
  return parsed.data.data;
}
