import { MATRIX, VISITS, expect, test } from './fixtures'

test('the reference study renders the expected visit by activity matrix', async ({ studyPage: page }) => {
  await expect(page.getByTestId('study-title')).toContainText('asthma')

  // Columns: the seven visits in study-day order, each with its day.
  const headers = page.locator('[data-testid^="visit-header-"]')
  await expect(headers).toHaveCount(VISITS.length)
  for (const [index, visit] of VISITS.entries()) {
    await expect(headers.nth(index)).toHaveAttribute('data-testid', `visit-header-${visit.id}`)
    await expect(headers.nth(index)).toContainText(visit.name)
    await expect(page.getByTestId(`visit-day-${visit.id}`)).toHaveValue(String(visit.day))
  }

  // Rows and cells: read the whole rendered matrix and compare it with the expected one.
  const rows = page.locator('[data-testid^="activity-row-"]')
  await expect(rows).toHaveCount(Object.keys(MATRIX).length)
  const rendered: Record<string, number[]> = {}
  for (const [activityId, { name }] of Object.entries(MATRIX)) {
    await expect(page.getByTestId(`activity-row-${activityId}`).locator('th')).toContainText(name)
    rendered[activityId] = []
    for (const visit of VISITS) {
      const scheduled = await page
        .getByTestId(`cell-${activityId}-${visit.id}`)
        .getAttribute('data-scheduled')
      rendered[activityId].push(scheduled === 'true' ? 1 : 0)
    }
  }
  expect(rendered).toEqual(Object.fromEntries(Object.entries(MATRIX).map(([id, row]) => [id, row.cells])))

  // The reference study is clean, and it is a single root version.
  await expect(page.getByTestId('findings-count')).toHaveText('0')
  await expect(page.getByTestId('findings-empty')).toBeVisible()
  await expect(page.getByTestId('timeline-version')).toHaveCount(1)
})
