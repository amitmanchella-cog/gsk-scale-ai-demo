import { expect, type Page } from '@playwright/test';
import path from 'node:path';

export const samplesDir = path.resolve(import.meta.dirname, '../../pda-api/samples');
export const weakProtocol = path.join(samplesDir, 't2d_phase3_weak.txt');

/** Upload a protocol file through the real file input and wait for the review page. */
export async function uploadProtocol(page: Page, file: string = weakProtocol) {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Upload a draft protocol' })).toBeVisible();
  await page.getByTestId('protocol-file').setInputFiles(file);
  await expect(page).toHaveURL(/\/protocols\/[0-9a-f-]{36}$/);
  await expect(page.getByTestId('design')).toBeVisible();
}

/** The page must never scroll sideways, on desktop or on the phone profile. */
export async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, 'page is wider than the viewport').toBeLessThanOrEqual(1);
}
