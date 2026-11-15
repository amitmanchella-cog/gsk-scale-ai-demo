import { FEV1_WARNING, expect, test } from './fixtures'

test('flagship: moving Week 12 to Day 99 warns on FEV1, retiming to Week 14 clears it', async ({
  studyPage: page,
}) => {
  const timeline = page.getByTestId('timeline-version')
  const findings = page.getByTestId('finding')
  await expect(timeline).toHaveCount(1)
  await expect(page.getByTestId('findings-count')).toHaveText('0')

  // Step 1: edit the Week 12 visit from Day 85 to Day 99.
  const day = page.getByTestId('visit-day-V-W12')
  await expect(day).toHaveValue('85')
  await day.fill('99')
  await day.press('Enter')

  // A new version appears, carrying exactly one warning on the primary endpoint.
  await expect(timeline).toHaveCount(2)
  await expect(timeline.nth(1)).toContainText('Move visit Week 12 to Day 99')
  await expect(timeline.nth(1)).toContainText('1 finding')
  await expect(day).toHaveValue('99')
  await expect(page.getByTestId('findings-count')).toHaveText('1')
  await expect(findings).toHaveCount(1)
  await expect(findings).toHaveAttribute('data-finding-id', 'unmet_endpoint_timepoint:EP-FEV1')
  await expect(findings).toContainText('Warning: Unmet endpoint timepoint')
  await expect(findings).toContainText(FEV1_WARNING)
  await page.screenshot({ path: test.info().outputPath('1-fev1-warning.png'), fullPage: true })

  // The finding links to its graph elements: the endpoint is highlighted in the graph view.
  await findings.getByRole('button').click()
  await page.getByTestId('tab-graph').click()
  await expect(page.getByTestId('graph-node-EP-FEV1')).toHaveAttribute('data-highlighted', 'true')
  await expect(page.getByTestId('graph-node-EP-ACQ5')).toHaveAttribute('data-highlighted', 'false')
  await page.getByTestId('tab-schedule').click()

  // Step 2: change the primary endpoint's timing to Week 14.
  await page.getByTestId('endpoint-week-EP-FEV1').fill('14')
  await page.getByTestId('retime-EP-FEV1').click()

  // Another version, and the study is consistent again.
  await expect(timeline).toHaveCount(3)
  await expect(timeline.nth(2)).toContainText('Change timing of Change from baseline in trough FEV1 to Week 14')
  await expect(timeline.nth(2)).toContainText('0 findings')
  await expect(page.getByTestId('findings-count')).toHaveText('0')
  await expect(findings).toHaveCount(0)
  await expect(page.getByTestId('findings-empty')).toBeVisible()
  await page.screenshot({ path: test.info().outputPath('2-consistent-again.png'), fullPage: true })

  // Each step is its own immutable version: the middle one still carries the warning,
  // and the root still has Week 12 on Day 85.
  await timeline.nth(1).getByRole('button').click()
  await expect(page.getByTestId('mode')).toHaveText('Read only')
  await expect(findings).toHaveCount(1)
  await expect(day).toHaveValue('99')
  await expect(day).toBeDisabled()
  await timeline.nth(0).getByRole('button').click()
  await expect(day).toHaveValue('85')
  await expect(page.getByTestId('findings-count')).toHaveText('0')
})

test('a rejected operation shows the reason and creates no version', async ({ studyPage: page }) => {
  // Two visits cannot share a study day: this is a structural error, not a warning.
  const day = page.getByTestId('visit-day-V-W12')
  await day.fill('29')
  await day.press('Enter')
  await expect(page.getByTestId('error')).toBeVisible()
  await expect(page.getByTestId('timeline-version')).toHaveCount(1)
  await expect(day).toHaveValue('85')
})
