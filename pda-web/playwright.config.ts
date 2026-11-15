import { defineConfig, devices } from '@playwright/test';
import { existsSync, mkdirSync } from 'node:fs';
import path from 'node:path';

const root = import.meta.dirname;
const apiDir = path.resolve(root, '../pda-api');
const venvPython = path.join(apiDir, '.venv/bin/python');
const python = process.env.PDA_API_PYTHON ?? (existsSync(venvPython) ? venvPython : 'python');
const database = path.join(root, '.e2e/pda-e2e.db');

mkdirSync(path.dirname(database), { recursive: true });

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: process.env.CI ? 2 : undefined,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  outputDir: 'test-results',
  use: {
    baseURL: 'http://localhost:3000',
    video: 'on',
    trace: 'on',
    screenshot: 'on',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'iphone-14', use: { ...devices['iPhone 14'] } },
  ],
  // The suite runs against the real API and the production builds of both packages.
  webServer: [
    {
      name: 'pda-api',
      // This file is evaluated by every worker, so the database is reset here, once, by the server command.
      command: `rm -f "${database}" && "${python}" -m uvicorn pda_api.main:app --port 8000`,
      cwd: apiDir,
      env: { DATABASE_URL: `sqlite+aiosqlite:///${database}` },
      url: 'http://localhost:8000/api/health',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      name: 'advisor',
      command: 'npm run build -w @pda/advisor && npm run preview -w @pda/advisor',
      url: 'http://localhost:3001/remoteEntry.js',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      name: 'host',
      command: 'npm run build -w @pda/host && npm run preview -w @pda/host',
      url: 'http://localhost:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
