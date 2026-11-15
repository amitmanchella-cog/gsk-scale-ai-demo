import { test as base, expect } from '@playwright/test'
import type { Page } from '@playwright/test'

/**
 * Every test works on its own copy of the synthetic reference study, created through the
 * same API the UI uses, so tests and browser engines can run in parallel.
 */
export const test = base.extend<{ studyId: string; studyPage: Page }>({
  studyId: async ({ request }, use) => {
    const response = await request.post('/api/studies', { data: {} })
    expect(response.status()).toBe(201)
    await use((await response.json()).id)
  },
  studyPage: async ({ page, studyId }, use) => {
    await page.goto(`/?study=${studyId}`)
    await expect(page.getByTestId('soa-grid')).toBeVisible()
    await use(page)
  },
})

export { expect }

export const VISITS = [
  { id: 'V-SCR', name: 'Screening', day: -14 },
  { id: 'V-RAND', name: 'Randomisation', day: 1 },
  { id: 'V-W4', name: 'Week 4', day: 29 },
  { id: 'V-W12', name: 'Week 12', day: 85 },
  { id: 'V-W24', name: 'Week 24', day: 169 },
  { id: 'V-W52', name: 'Week 52', day: 365 },
  { id: 'V-FU', name: 'Follow-up', day: 393 },
] as const

/** The expected visit by activity matrix of the reference study, written out by hand. */
//                                                   SCR RAND W4 W12 W24 W52 FU
export const MATRIX: Record<string, { name: string; cells: number[] }> = {
  'A-ICF': { name: 'Informed consent', cells: [1, 0, 0, 0, 0, 0, 0] },
  'A-ELIG': { name: 'Eligibility check', cells: [1, 1, 0, 0, 0, 0, 0] },
  'A-SPIRO': { name: 'Spirometry', cells: [1, 1, 1, 1, 1, 1, 0] },
  'A-ACQ5': { name: 'ACQ-5', cells: [0, 1, 1, 1, 1, 1, 0] },
  'A-VITALS': { name: 'Vital signs', cells: [1, 1, 1, 1, 1, 1, 0] },
  'A-LABS': { name: 'Labs', cells: [1, 1, 0, 1, 1, 1, 0] },
  'A-AE': { name: 'Adverse event review', cells: [0, 0, 1, 1, 1, 1, 1] },
  'A-DISP': { name: 'Study drug dispensing', cells: [0, 1, 1, 1, 1, 0, 0] },
}

export const FEV1_WARNING =
  'Primary endpoint "Change from baseline in trough FEV1" is timed at Week 12 (Day 85), ' +
  'but no visit performs Spirometry within its window of that day. ' +
  'The nearest is "Week 12" on Day 99 (window of 3 days).'
