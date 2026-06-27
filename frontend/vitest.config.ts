import { defineConfig, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config';

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      coverage: {
        provider: 'v8',
        reporter: ['text', 'lcov'],
        thresholds: {
          lines: 80,
          functions: 80,
          branches: 70,
        },
        exclude: [
          'src/test/**',
          '**/*.config.*',
          '**/*.config.js',
          '**/.eslintrc.*',
          '**/index.ts',
          'src/main.tsx',
          'src/vite-env.d.ts',
          'src/App.tsx',
          // Router — covered by E2E tests (Playwright), not unit tests
          'src/router/**',
          // Zustand store — trivial setters, exercised via component tests
          'src/store/**',
          // SSE hook + chat session — require real fetch ReadableStream, covered by E2E
          'src/shared/hooks/useSSE.ts',
          'src/features/chat/useChatSession.ts',
          // Pure type re-exports — no runtime code
          'src/shared/types/types.ts',
          // Page components — thin compositions, covered by E2E
          'src/components/pages/**',
          // New premium UI organisms — thin compositions, covered by E2E
          'src/components/organisms/TopBar/**',
          'src/components/organisms/ChatArea/**',
          'src/components/organisms/ChatInputArea/**',
          'src/components/organisms/SummarySlideOver/**',
          // New premium UI molecules — covered by E2E
          'src/components/molecules/DocumentStatusWidget/**',
          'src/components/molecules/PremiumMessageBubble/**',
          // Templates — thin layout wrappers, covered by E2E
          'src/components/templates/**',
          'node_modules/**',
        ],
        include: ['src/**/*.{ts,tsx}'],
      },
    },
  }),
);
