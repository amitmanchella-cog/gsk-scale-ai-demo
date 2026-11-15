import { expect, test } from '@playwright/test';
import { expectNoHorizontalOverflow, uploadProtocol } from './fixtures';

test.describe('author journey on the weak sample protocol', () => {
  test('upload, extracted design, red flags and competing trials', async ({ page }) => {
    await uploadProtocol(page);

    await test.step('extracted design', async () => {
      await expect(page.getByTestId('fact-indication')).toHaveText('Type 2 diabetes');
      await expect(page.getByTestId('fact-phase')).toHaveText('Phase 3');
      await expect(page.getByTestId('fact-enrollment')).toHaveText('900');
      await expect(page.getByTestId('fact-sites')).toHaveText('8');
      await expect(page.getByTestId('fact-age')).toHaveText('40 to 60 years');
      await expect(page.getByTestId('fact-countries')).toHaveText('United States (5), China (3)');
      await page.getByTestId('criteria-toggle').click();
      await expect(page.getByTestId('criterion-I3')).toContainText('HbA1c');
      await expect(page.locator('[data-testid^="criterion-I"]')).toHaveCount(9);
      await expect(page.locator('[data-testid^="criterion-E"]')).toHaveCount(15);
    });

    await test.step('red-flag restrictiveness scores', async () => {
      const section = page.getByTestId('restrictiveness');
      await expect(section).toBeVisible();
      const redFlags = Number(await section.getByTestId('red-flag-count').innerText());
      expect(redFlags).toBeGreaterThanOrEqual(4);
      await expect(section.getByTestId('criterion-score')).toHaveCount(24);

      // Sorted from most to least restrictive, every score within 0-100.
      const values = (await section.getByTestId('score-value').allInnerTexts()).map(Number);
      expect(values.every((value) => value >= 0 && value <= 100)).toBe(true);
      expect(values).toEqual([...values].sort((a, b) => b - a));

      await section.getByTestId('only-red-flags').check();
      await expect(section.getByTestId('criterion-score')).toHaveCount(redFlags);
      await expect(section.locator('[data-testid="criterion-score"][data-level="high"]')).toHaveCount(redFlags);

      // The benchmark trials that drive the top score are listed and link to the registry.
      const top = section.getByTestId('criterion-score').first();
      await top.locator('summary').click();
      const driving = top.getByTestId('driving-trials').getByRole('link');
      await expect(driving.first()).toBeVisible();
      await expect(driving.first()).toHaveAttribute('href', /clinicaltrials\.gov\/study\/NCT\d{8}$/);
    });

    await test.step('competing recruiting trials per planned country', async () => {
      const countries = page.getByTestId('competing-country');
      await expect(countries).toHaveCount(2);
      await expect(countries.nth(0)).toContainText('United States');
      await expect(countries.nth(0)).toContainText('Crowded');
      await expect(countries.nth(1)).toContainText('China');
      expect(Number(await countries.nth(0).getByTestId('competing-count').innerText())).toBeGreaterThan(0);
    });

    await test.step('similar benchmark trials', async () => {
      await page.getByTestId('similar-toggle').click();
      const rows = await page.getByTestId('similar-trial').count();
      expect(rows).toBeGreaterThanOrEqual(20);
      expect(rows).toBeLessThanOrEqual(50);
    });

    await expectNoHorizontalOverflow(page);
  });

  test('a sample can be loaded from the upload page and the review survives a reload', async ({ page }) => {
    await page.goto('/');
    await page.getByTestId('sample-t2d_phase3_weak').click();
    await expect(page.getByTestId('fact-indication')).toHaveText('Type 2 diabetes');
    await page.reload();
    await expect(page.getByTestId('fact-enrollment')).toHaveText('900');
    await expectNoHorizontalOverflow(page);

    await page.getByTestId('start-over').click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole('heading', { name: 'Upload a draft protocol' })).toBeVisible();
  });

  test('an unusable document is rejected with the reason', async ({ page }) => {
    await page.goto('/');
    await page.getByTestId('protocol-file').setInputFiles({
      name: 'notes.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('Minutes of a meeting about nothing in particular.'),
    });
    const alert = page.getByRole('alert');
    await expect(alert).toContainText('Could not extract indication.');
    await expect(page).toHaveURL(/\/$/);
  });
});
