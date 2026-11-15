import path from 'node:path';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  // In unit tests the federated remote resolves straight to its source.
  resolve: {
    alias: { 'advisor/AdvisorApp': path.resolve(import.meta.dirname, 'packages/advisor/src/AdvisorApp.tsx') },
  },
  test: {
    environment: 'jsdom',
    include: ['packages/*/src/**/*.test.{ts,tsx}'],
    setupFiles: ['./vitest.setup.ts'],
    css: false,
    coverage: {
      provider: 'v8',
      include: ['packages/*/src/**/*.{ts,tsx}'],
      exclude: ['**/*.test.{ts,tsx}', '**/*.d.ts', '**/index.ts', '**/bootstrap.tsx', '**/types.ts', '**/test-data.ts'],
      reporter: ['text', 'lcov'],
      thresholds: { lines: 80, functions: 80, statements: 80, branches: 70 },
    },
  },
});
