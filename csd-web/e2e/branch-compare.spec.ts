import { expect, test } from './fixtures'
import type { Page } from '@playwright/test'

/** Start a branch from the version on screen and wait until the UI has switched to it. */
async function createBranch(page: Page, name: string) {
  await page.getByTestId('branch-name').fill(name)
  await page.getByTestId('create-branch').click()
  await expect(page.getByTestId('current-branch')).toHaveText(name)
  await expect(page.getByTestId('branch-select')).toHaveValue(name)
  await expect(page.getByTestId('mode')).toHaveText('Editing head')
}

test('two branches compare side by side: fewer visits against ACQ-5 as primary', async ({
  studyPage: page,
}) => {
  const timeline = page.getByTestId('timeline-version')
  // The reference study, by hand: 7 visits, 640 minutes, cost proxy 2160.
  await expect(page.getByTestId('score-visit_count')).toHaveText('7')
  await expect(page.getByTestId('score-patient_time_minutes')).toHaveText('640 min')
  await expect(page.getByTestId('score-cost_proxy')).toHaveText('2160')

  // Branch 1: remove the Week 4 visit.
  await createBranch(page, 'fewer-visits')
  await expect(timeline).toHaveCount(1) // a new branch creates no version
  await page.getByTestId('remove-visit-V-W4').click()
  await expect(timeline).toHaveCount(2)
  await expect(timeline.nth(1)).toContainText('Remove visit Week 4')
  await expect(page.getByTestId('visit-header-V-W4')).toHaveCount(0)
  await expect(page.locator('[data-testid^="visit-header-"]')).toHaveCount(6)
  await expect(page.getByTestId('score-visit_count')).toHaveText('6')
  await expect(page.getByTestId('score-patient_time_minutes')).toHaveText('550 min')
  await expect(page.getByTestId('score-cost_proxy')).toHaveText('1940')
  await expect(page.getByTestId('findings-count')).toHaveText('0')

  // Main is untouched: it still has Week 4 and a single version.
  await page.getByTestId('branch-select').selectOption('main')
  await expect(page.getByTestId('current-branch')).toHaveText('main')
  await expect(page.getByTestId('visit-header-V-W4')).toBeVisible()
  await expect(timeline).toHaveCount(1)
  await expect(page.getByTestId('score-visit_count')).toHaveText('7')

  // Branch 2, also from the root: ACQ-5 becomes the primary endpoint.
  await createBranch(page, 'acq5-primary')
  await page.getByTestId('make-primary-EP-ACQ5').click()
  await expect(timeline).toHaveCount(2)
  await expect(timeline.nth(1)).toContainText('the primary endpoint')
  await expect(page.getByTestId('endpoint-EP-ACQ5')).toContainText('primary')
  await expect(page.getByTestId('make-primary-EP-FEV1')).toBeVisible()
  await expect(page.getByTestId('make-primary-EP-ACQ5')).toHaveCount(0)
  await expect(page.getByTestId('visit-header-V-W4')).toBeVisible()

  // Compare the two branches.
  await page.getByTestId('tab-compare').click()
  await page.getByTestId('compare-left').selectOption('fewer-visits')
  await page.getByTestId('compare-right').selectOption('acq5-primary')
  await expect(page.getByTestId('compare-head-left')).toHaveText('fewer-visits')
  await expect(page.getByTestId('compare-head-right')).toHaveText('acq5-primary')

  const expected = {
    visit_count: ['6', '7', '+1'],
    patient_time_minutes: ['550 min', '640 min', '+90 min'],
    cost_proxy: ['1940', '2160', '+220'],
  }
  for (const [key, [left, right, delta]] of Object.entries(expected)) {
    await expect(page.getByTestId(`compare-left-${key}`)).toHaveText(left!)
    await expect(page.getByTestId(`compare-right-${key}`)).toHaveText(right!)
    await expect(page.getByTestId(`compare-delta-${key}`)).toHaveText(delta!)
  }

  // Side by side means side by side: the two score columns share a row, left of right,
  // on every engine and on the tablet layout.
  const leftBox = (await page.getByTestId('compare-left-visit_count').boundingBox())!
  const rightBox = (await page.getByTestId('compare-right-visit_count').boundingBox())!
  expect(Math.abs(leftBox.y - rightBox.y)).toBeLessThan(2)
  expect(leftBox.x + leftBox.width).toBeLessThanOrEqual(rightBox.x + 1)

  await expect(page.getByTestId('compare-findings-left')).toContainText('0 findings')
  await expect(page.getByTestId('compare-findings-right')).toContainText('0 findings')
  const changes = page.getByTestId('compare-change')
  await expect(changes).toHaveCount(8)
  await expect(page.locator('[data-element-id="V-W4"]')).toHaveAttribute('data-change', 'added')
  await expect(page.locator('[data-element-id="EP-ACQ5"]')).toHaveAttribute('data-change', 'changed')
  await expect(page.locator('[data-element-id="EP-FEV1"]')).toHaveAttribute('data-change', 'changed')
  await page.screenshot({ path: test.info().outputPath('branch-compare.png'), fullPage: true })

  // Against main, the fewer-visits branch is lighter on all three scores.
  await page.getByTestId('compare-left').selectOption('main')
  await page.getByTestId('compare-right').selectOption('fewer-visits')
  await expect(page.getByTestId('compare-delta-visit_count')).toHaveText('-1')
  await expect(page.getByTestId('compare-delta-patient_time_minutes')).toHaveText('-90 min')
  await expect(page.getByTestId('compare-delta-cost_proxy')).toHaveText('-220')
})

test('a branch can start from an older version that is no longer a head', async ({
  studyPage: page,
}) => {
  const timeline = page.getByTestId('timeline-version')
  const day = page.getByTestId('visit-day-V-W12')
  await day.fill('99')
  await day.press('Enter')
  await expect(timeline).toHaveCount(2)
  await expect(page.getByTestId('findings-count')).toHaveText('1')

  // Go back to the root, which is read only on main, and branch from it.
  await timeline.nth(0).getByRole('button').click()
  await expect(page.getByTestId('mode')).toHaveText('Read only')
  await createBranch(page, 'from-root')
  await expect(day).toHaveValue('85')
  await expect(day).toBeEnabled()
  await page.getByTestId('remove-visit-V-W24').click()
  await expect(timeline).toHaveCount(2)
  await expect(timeline.nth(1)).toContainText('Remove visit Week 24')

  // Removing Week 24 leaves the ACQ-5 endpoint at Week 24 unmet: compare shows main's
  // FEV1 warning on the left and the branch's ACQ-5 warning on the right.
  await page.getByTestId('tab-compare').click()
  await expect(page.getByTestId('compare-head-right')).toHaveText('from-root')
  await expect(page.getByTestId('compare-findings-left')).toContainText('1 finding')
  await expect(page.getByTestId('compare-findings-left')).toContainText('trough FEV1')
  await expect(page.getByTestId('compare-findings-right')).toContainText('1 finding')
  await expect(page.getByTestId('compare-findings-right')).toContainText('ACQ-5')
})
