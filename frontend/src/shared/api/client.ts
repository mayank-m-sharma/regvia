import axios, { type AxiosError } from 'axios';
import { ApiError } from './errors';
import { useAuthStore } from '@/store/authStore';

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

// Request interceptor: attach JWT from authStore
apiClient.interceptors.request.use((config) => {
  const { token } = useAuthStore.getState();
  if (token) {
    // eslint-disable-next-line no-param-reassign
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: unwrap envelope, handle 401, throw ApiError on business errors
apiClient.interceptors.response.use(
  (response) => {
    const envelope = response.data as ApiEnvelope;
    if (envelope.error !== null && envelope.error !== undefined) {
      throw new ApiError(envelope.error.code, envelope.error.message);
    }
    return response;
  },
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = '/';
    }
    return Promise.reject(error);
  },
);

export default apiClient;
