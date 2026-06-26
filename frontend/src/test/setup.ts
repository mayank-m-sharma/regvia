import '@testing-library/jest-dom';
import {
  afterAll,
  afterEach,
  beforeAll,
  vi,
} from 'vitest';
import { server } from './server';

// Suppress React Router v6 → v7 future flag warnings in test output
vi.spyOn(console, 'warn').mockImplementation((msg: unknown) => {
  if (typeof msg === 'string' && msg.includes('React Router Future Flag Warning')) return;
  console.warn(msg);
});

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
