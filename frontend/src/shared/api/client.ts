import axios, { type AxiosError } from 'axios';
import { ApiError } from './errors';

const apiClient = axios.create({
  // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

interface ApiEnvelope {
  data: unknown;
  error: { message: string; code: string } | null;
}

// Response interceptor: unwrap envelope and throw ApiError on business errors
apiClient.interceptors.response.use(
  (response) => {
    const envelope = response.data as ApiEnvelope;
    if (envelope.error !== null && envelope.error !== undefined) {
      throw new ApiError(envelope.error.code, envelope.error.message);
    }
    return response;
  },
  (error: AxiosError) => Promise.reject(error),
);

export default apiClient;
