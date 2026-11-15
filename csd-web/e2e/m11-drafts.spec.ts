import { expect, test } from './fixtures'

test('M11 section 8: clicking a sentence highlights the graph elements it came from', async ({
  studyPage: page,
}) => {
  await page.getByTestId('tab-drafts').click()
  await expect(page.getByTestId('draft-title')).toHaveText('8 Trial Assessments and Procedures')
  await expect(page.getByTestId('draft-provider')).toContainText('template provider, offline')

  // One sentence per visit, per activity and per operational standard: 7 + 8 + 4.
  const sentences = page.getByTestId('draft-sentence')
  await expect(sentences).toHaveCount(19)
  for (const sentence of await sentences.all())
    expect((await sentence.getAttribute('data-element-ids'))?.trim()).toBeTruthy()

  // Nothing is highlighted before a sentence is clicked.
  await expect(page.locator('[data-highlighted="true"]')).toHaveCount(0)

  const week4 = sentences.filter({ hasText: /^Week 4 takes place/ })
  await expect(week4).toHaveText(
    'Week 4 takes place on site on Day 29 (window of 3 days either side) and includes ' +
      'spirometry, ACQ-5, vital signs, adverse event review and study drug dispensing.',
  )
  await week4.click()
  await expect(week4).toHaveAttribute('aria-pressed', 'true')

  // The linked elements: the Week 4 visit and the cells of its column, and nothing else.
  const header = page.getByTestId('visit-header-V-W4')
  await expect(header).toHaveAttribute('data-highlighted', 'true')
  await expect(header).toBeVisible()
  await expect(page.getByTestId('cell-A-SPIRO-V-W4')).toHaveAttribute('data-highlighted', 'true')
  await expect(page.getByTestId('cell-A-SPIRO-V-W12')).toHaveAttribute('data-highlighted', 'false')
  await expect(page.getByTestId('visit-header-V-W12')).toHaveAttribute('data-highlighted', 'false')
  await expect(page.locator('th[data-highlighted="true"]')).toHaveCount(1)
  // The highlight is painted, not only flagged.
  await expect(page.getByTestId('cell-A-SPIRO-V-W4')).toHaveCSS(
    'background-color',
    'rgb(255, 246, 207)',
  )
  await expect(page.getByTestId('cell-A-SPIRO-V-W12')).not.toHaveCSS(
    'background-color',
    'rgb(255, 246, 207)',
  )

  // The same element is lit in the plan graph below the grid.
  await expect(page.getByTestId('graph-node-V-W4')).toHaveAttribute('data-highlighted', 'true')
  await expect(page.getByTestId('graph-node-V-W12')).toHaveAttribute('data-highlighted', 'false')
  await expect(page.locator('.graph-node[data-highlighted="true"]')).toHaveCount(1)

  // An activity sentence links to its row and to exactly the cells where it is scheduled.
  const consent = sentences.filter({
    hasText: /^Informed consent is performed/,
  })
  await expect(consent).toHaveText('Informed consent is performed at 1 visit: Screening.')
  await consent.click()
  await expect(page.getByTestId('activity-row-A-ICF')).toHaveAttribute('data-highlighted', 'true')
  await expect(page.getByTestId('cell-A-ICF-V-SCR')).toHaveAttribute('data-highlighted', 'true')
  await expect(page.getByTestId('visit-header-V-W4')).toHaveAttribute('data-highlighted', 'false')
  await expect(page.getByTestId('graph-node-A-ICF')).toHaveAttribute('data-highlighted', 'true')
  await expect(page.getByTestId('graph-node-V-W4')).toHaveAttribute('data-highlighted', 'false')
  await expect(week4).toHaveAttribute('aria-pressed', 'false')
  await page.screenshot({
    path: test.info().outputPath('m11-section-8.png'),
    fullPage: true,
  })

  // The highlighted node is really on screen, in every engine and on the tablet layout.
  const node = page.getByTestId('graph-node-A-ICF')
  await node.scrollIntoViewIfNeeded()
  await expect(node).toBeInViewport()
  await page.screenshot({ path: test.info().outputPath('m11-section-8-graph.png') })
})

test('M11 sections 3 and 5 link to the intent graph and follow the version', async ({
  studyPage: page,
}) => {
  // The flagship edits, so the draft has something to follow.
  const day = page.getByTestId('visit-day-V-W12')
  await day.fill('99')
  await day.press('Enter')
  await expect(page.getByTestId('findings-count')).toHaveText('1')
  await page.getByTestId('endpoint-week-EP-FEV1').fill('14')
  await page.getByTestId('retime-EP-FEV1').click()
  await expect(page.getByTestId('findings-count')).toHaveText('0')

  await page.getByTestId('tab-drafts').click()
  await expect(
    page.getByTestId('draft-sentence').filter({ hasText: /^Week 12 takes place/ }),
  ).toContainText('on Day 99')

  await page.getByTestId('draft-section-5').click()
  await expect(page.getByTestId('draft-title')).toHaveText('5 Trial Design')
  const primary = page.getByTestId('draft-sentence').filter({ hasText: /^The primary endpoint/ })
  await expect(primary).toHaveText(
    'The primary endpoint, change from baseline in trough FEV1, is assessed at Week 14 (Day 99).',
  )
  await primary.click()
  await expect(page.getByTestId('graph-node-EP-FEV1')).toHaveAttribute('data-highlighted', 'true')
  await expect(page.getByTestId('graph-node-EP-ACQ5')).toHaveAttribute('data-highlighted', 'false')

  await page.getByTestId('draft-section-3').click()
  await expect(page.getByTestId('draft-title')).toHaveText(
    '3 Trial Objectives and Associated Estimands',
  )
  const objective = page.getByTestId('draft-sentence').first()
  await expect(objective).toContainText('The primary objective is')
  await objective.click()
  await expect(page.getByTestId('graph-node-OBJ-PRIM')).toHaveAttribute('data-highlighted', 'true')
  await expect(page.locator('.graph-node[data-highlighted="true"]')).toHaveCount(1)

  // The draft of the root version still says Week 12.
  await page.getByTestId('timeline-version').first().click()
  await page.getByTestId('draft-section-5').click()
  await expect(
    page.getByTestId('draft-sentence').filter({ hasText: /^The primary endpoint/ }),
  ).toContainText('Week 12 (Day 85)')
})
