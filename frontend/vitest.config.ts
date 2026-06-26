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
          // Placeholder stubs — covered when implemented in E8+
          'src/App.tsx',
          'node_modules/**',
        ],
        include: ['src/**/*.{ts,tsx}'],
      },
    },
  }),
);
