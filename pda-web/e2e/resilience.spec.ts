import { expect, test } from '@playwright/test';

test('the host shell still renders when the Advisor remote is down', async ({ page }) => {
  // Same effect as stopping the Advisor server: its entry file cannot be fetched.
  await page.route('**/remoteEntry.js', (route) => route.abort('connectionrefused'));
  await page.goto('/');

  await expect(page.getByTestId('shell-header')).toBeVisible();
  const fallback = page.getByTestId('remote-fallback');
  await expect(fallback).toBeVisible();
  await expect(fallback).toContainText('The Advisor is temporarily unavailable');
  await expect(page.getByTestId('advisor')).toHaveCount(0);

  // Pages owned by the shell keep working.
  await page.getByRole('link', { name: 'About' }).click();
  await expect(page.getByTestId('about')).toBeVisible();
});

test('the shell recovers once the Advisor remote is reachable again', async ({ page }) => {
  await page.route('**/remoteEntry.js', (route) => route.abort('connectionrefused'));
  await page.goto('/');
  await expect(page.getByTestId('remote-fallback')).toBeVisible();

  await page.unroute('**/remoteEntry.js');
  await page.getByRole('button', { name: 'Try again' }).click();
  await expect(page.getByTestId('advisor')).toBeVisible();
});
