import { readFile } from 'node:fs/promises';
import { expect, test } from '@playwright/test';
import { expectNoHorizontalOverflow, uploadProtocol } from './fixtures';

test.describe('author journey on the weak sample protocol', () => {
  test('upload, design, red flags, forecast, suggestions, what-if and report export', async ({ page }, testInfo) => {
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

    let draftP50 = 0;
    await test.step('P50, P90 and termination risk', async () => {
      const forecast = page.getByTestId('forecast');
      await expect(forecast).toBeVisible();
      draftP50 = Number((await forecast.getByTestId('forecast-p50').innerText()).replaceAll(',', ''));
      const p90 = Number((await forecast.getByTestId('forecast-p90').innerText()).replaceAll(',', ''));
      expect(draftP50).toBeGreaterThan(0);
      expect(p90).toBeGreaterThan(draftP50);
      await expect(forecast.getByTestId('termination-risk-value')).toHaveText(/^\d+(\.\d)?%$/);
      await expect(forecast.getByTestId('termination-risk')).toHaveAttribute('data-level', 'high');
      await forecast.locator('summary').click();
      await expect(forecast.getByTestId('termination-trials').getByRole('link').first()).toHaveAttribute(
        'href',
        /clinicaltrials\.gov\/study\/NCT\d{8}$/,
      );
    });

    await test.step('every suggestion cites at least 5 benchmark trials', async () => {
      const suggestions = page.getByTestId('suggestion');
      const count = await suggestions.count();
      expect(count).toBeGreaterThanOrEqual(2);
      for (let index = 0; index < count; index += 1) {
        const suggestion = suggestions.nth(index);
        await suggestion.locator('summary').click();
        const ids = await suggestion.getByTestId('citation').allInnerTexts();
        expect(ids.length, await suggestion.getByTestId('suggestion-title').innerText()).toBeGreaterThanOrEqual(5);
        expect(new Set(ids).size).toBe(ids.length);
        expect(ids.every((id) => /^NCT\d{8}$/.test(id))).toBe(true);
      }
    });

    await test.step('two changes in what-if improve the forecast in under 5 seconds', async () => {
      const picks = page.getByTestId('suggestion-pick');
      await picks.nth(0).check();
      await picks.nth(1).check();
      await expect(page.getByTestId('what-if-selected').getByRole('listitem')).toHaveCount(2);

      const started = Date.now();
      await page.getByTestId('what-if-run').click();
      await expect(page.getByTestId('what-if-result')).toBeVisible({ timeout: 5000 });
      expect(Date.now() - started).toBeLessThan(5000);

      const scenarioP50 = Number((await page.getByTestId('what-if-p50').innerText()).replaceAll(',', ''));
      expect(scenarioP50).toBeLessThan(draftP50);
      expect(Number(await page.getByTestId('what-if-seconds').innerText())).toBeLessThan(5);
      expect(Number((await page.getByTestId('what-if-p50-saved').innerText()).replaceAll(',', ''))).toBeLessThan(0);
      // Kept with the other artifacts so a reviewer can compare the panel across engines.
      for (const section of ['forecast', 'suggestions', 'export']) {
        const path = testInfo.outputPath(`${section}.png`);
        await page.getByTestId(section).screenshot({ path });
        await testInfo.attach(section, { path, contentType: 'image/png' });
      }
    });

    await test.step('the exported report contains the accepted changes and their cited trials', async () => {
      const accepted: { title: string; cited: string[] }[] = [];
      for (const suggestion of await page.locator('[data-testid="suggestion"]:has(input:checked)').all()) {
        accepted.push({
          title: await suggestion.getByTestId('suggestion-title').innerText(),
          cited: await suggestion.getByTestId('citation').allTextContents(),
        });
      }
      expect(accepted).toHaveLength(2);
      const scenarioP50 = await page.getByTestId('what-if-p50').innerText();
      await expect(page.getByTestId('export-summary')).toContainText('2 accepted changes');

      const [htmlDownload] = await Promise.all([
        page.waitForEvent('download'),
        page.getByTestId('export-html').click(),
      ]);
      expect(htmlDownload.suggestedFilename()).toMatch(/^design-review-.+\.html$/);
      const htmlPath = testInfo.outputPath('design-review.html');
      await htmlDownload.saveAs(htmlPath);
      const html = await readFile(htmlPath, 'utf8');
      expect(html).toContain('4. Accepted changes');
      // Each change's trials are looked for under that change's own heading, not in the whole report.
      for (const { title, cited } of accepted) {
        const start = html.indexOf(`${title}</h3>`);
        expect(start).toBeGreaterThan(html.indexOf('4. Accepted changes'));
        const change = html.slice(start, html.indexOf('<h', start + title.length + 5));
        expect(cited.length).toBeGreaterThanOrEqual(5);
        expect(change).toContain(`Cited benchmark trials (${cited.length})`);
        for (const id of cited) expect(change).toContain(`>${id}</a>`);
      }
      expect(html).toContain('With accepted changes');
      expect(html).toContain(`<td>${scenarioP50}</td>`);
      await testInfo.attach('design-review.html', { path: htmlPath, contentType: 'text/html' });

      const [pdfDownload] = await Promise.all([page.waitForEvent('download'), page.getByTestId('export-pdf').click()]);
      expect(pdfDownload.suggestedFilename()).toMatch(/^design-review-.+\.pdf$/);
      const pdfPath = testInfo.outputPath('design-review.pdf');
      await pdfDownload.saveAs(pdfPath);
      const pdf = await readFile(pdfPath);
      expect(pdf.subarray(0, 5).toString()).toBe('%PDF-');
      expect(pdf.length).toBeGreaterThan(10_000);
      await testInfo.attach('design-review.pdf', { path: pdfPath, contentType: 'application/pdf' });
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
