import { defineConfig, devices } from '@playwright/test'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const API_PORT = Number(process.env.CSD_API_PORT ?? 8000)
const WEB_PORT = Number(process.env.CSD_WEB_PORT ?? 4173)
const API_URL = `http://127.0.0.1:${API_PORT}`
// The interpreter that has csd-api installed (see the README).
const PYTHON = process.env.CSD_PYTHON ?? 'python'
// The real API on a throwaway SQLite database; every test creates its own study in it.
const DATABASE = join(mkdtempSync(join(tmpdir(), 'csd-e2e-')), 'csd.db')

export default defineConfig({
  testDir: './e2e',
  outputDir: './test-results',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: process.env.CI ? 2 : undefined,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['json', { outputFile: 'playwright-report/results.json' }],
  ],
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    video: 'on',
    trace: 'on',
    screenshot: 'on',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'webkit-ipad', use: { ...devices['iPad Pro 11'] } },
  ],
  webServer: [
    {
      command: `${PYTHON} -m uvicorn csd_api.main:app --host 127.0.0.1 --port ${API_PORT}`,
      url: `${API_URL}/health`,
      env: { CSD_DATABASE_URL: `sqlite:///${DATABASE}` },
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `npm run build && npm run preview -- --host 127.0.0.1 --port ${WEB_PORT} --strictPort`,
      url: `http://127.0.0.1:${WEB_PORT}`,
      env: { CSD_API_URL: API_URL },
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
})
