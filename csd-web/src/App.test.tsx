import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, studyIdFromLocation } from './App'
import { comparison, draft, grid, summaries, version } from './fixtures'

// React Flow needs a real layout engine; the graph view is covered by the Playwright suite.
vi.mock('./components/GraphView', () => ({
  GraphView: ({ highlight }: { highlight: ReadonlySet<string> }) => (
    <div data-testid="graph-view">{[...highlight].join(',')}</div>
  ),
}))

/** A tiny in-memory stand-in for csd-api, at the fetch boundary. */
function fakeApi() {
  let head = 'v-0'
  const branches = [{ study_id: 's', name: 'main', base_version_id: null as string | null }]
  const calls: { path: string; body?: unknown }[] = []
  const respond = (status: number, body: unknown) =>
    Promise.resolve(new Response(JSON.stringify(body), { status }))
  vi.stubGlobal('fetch', (input: string, init?: RequestInit) => {
    const path = input.replace('/api', '')
    const body = init?.body ? JSON.parse(String(init.body)) : undefined
    calls.push({ path, body })
    if (path === '/operation-types') return respond(200, ['MoveVisit', 'ChangeEndpointTiming'])
    if (path.endsWith('/versions')) return respond(200, head === 'v-0' ? summaries.slice(0, 1) : summaries)
    if (path.endsWith('/branches') && body) {
      if (body.name === 'taken') return respond(422, { detail: "branch 'taken' already exists" })
      branches.push({ study_id: 's', name: body.name, base_version_id: 'v-0' })
      return respond(201, { ...branches.at(-1), head_version_id: 'v-0' })
    }
    if (path.endsWith('/branches'))
      return respond(200, branches.map((branch) => ({ ...branch, head_version_id: head })))
    if (path.endsWith('/score'))
      return respond(200, { visit_count: 7, patient_time_minutes: 640, cost_proxy: 2160 })
    if (path.endsWith('/drafts')) return respond(200, draft)
    if (path.startsWith('/compare')) return respond(200, comparison)
    if (path.endsWith('/schedule')) return respond(200, grid)
    if (path.includes('/operations')) {
      if (body.day === 1) return respond(422, { detail: 'two visits on Day 1' })
      head = 'v-1'
      return respond(201, version('v-1'))
    }
    if (path === '/versions/v-0') return respond(200, version('v-0'))
    if (path === '/versions/v-1') return respond(200, version('v-1'))
    return respond(404, { detail: `study 'nope' not found` })
  })
  return calls
}

afterEach(() => vi.unstubAllGlobals())

describe('App', () => {
  it('reads the study from the query string and defaults to the reference study', () => {
    expect(studyIdFromLocation('?study=sandbox-1')).toBe('sandbox-1')
    expect(studyIdFromLocation('')).toBe('asthma-ref')
  })

  it('loads the head version, applies an operation and shows the new version and finding', async () => {
    const calls = fakeApi()
    render(<App />)
    expect(await screen.findByTestId('soa-grid')).toBeVisible()
    expect(screen.getByTestId('current-version')).toHaveTextContent('v0 (v-0)')
    expect(screen.getByTestId('mode')).toHaveTextContent('Editing head')
    expect(screen.getByTestId('findings-count')).toHaveTextContent('0')

    const day = screen.getByLabelText('Study day for Week 12')
    await userEvent.clear(day)
    await userEvent.type(day, '99{Enter}')

    await waitFor(() => expect(screen.getByTestId('current-version')).toHaveTextContent('v1 (v-1)'))
    expect(calls).toContainEqual({
      path: '/versions/v-0/operations?branch=main',
      body: { type: 'MoveVisit', visit_id: 'V-W12', day: 99 },
    })
    expect(screen.getAllByTestId('timeline-version')).toHaveLength(2)
    expect(screen.getByTestId('findings-count')).toHaveTextContent('1')

    // Clicking the finding highlights its graph elements; older versions are read only.
    await userEvent.click(screen.getByTestId('finding').querySelector('button')!)
    await userEvent.click(screen.getByTestId('tab-graph'))
    expect(screen.getByTestId('graph-view')).toHaveTextContent('EP-FEV1,DA-SPIRO')
    await userEvent.click(screen.getByRole('button', { name: 'Clear highlight' }))
    expect(screen.getByTestId('graph-view')).toHaveTextContent('')

    await userEvent.click(screen.getAllByTestId('timeline-version')[0]!.querySelector('button')!)
    await waitFor(() => expect(screen.getByTestId('mode')).toHaveTextContent('Read only'))
  })

  it('shows the API reason when an operation is rejected, and no version is added', async () => {
    fakeApi()
    render(<App />)
    const day = await screen.findByLabelText('Study day for Week 12')
    await userEvent.clear(day)
    await userEvent.type(day, '1{Enter}')
    expect(await screen.findByRole('alert')).toHaveTextContent('two visits on Day 1')
    expect(screen.getAllByTestId('timeline-version')).toHaveLength(1)
    await userEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('creates a branch from the version on screen, edits it and compares it with main', async () => {
    const calls = fakeApi()
    render(<App />)
    expect(await screen.findByTestId('score-visit_count')).toHaveTextContent('7')
    expect(screen.getByTestId('score-patient_time_minutes')).toHaveTextContent('640 min')
    expect(screen.getByTestId('current-branch')).toHaveTextContent('main')

    await userEvent.type(screen.getByTestId('branch-name'), 'fewer-visits')
    await userEvent.click(screen.getByTestId('create-branch'))
    await waitFor(() => expect(screen.getByTestId('current-branch')).toHaveTextContent('fewer-visits'))
    expect(calls).toContainEqual({ path: '/versions/v-0/branches', body: { name: 'fewer-visits' } })
    expect(screen.getByTestId('branch-select')).toHaveValue('fewer-visits')
    expect(screen.getByTestId('mode')).toHaveTextContent('Editing head')

    // The first operation on the branch is posted to its base version, naming the branch.
    await userEvent.click(screen.getByTestId('remove-visit-V-W12'))
    await waitFor(() =>
      expect(calls).toContainEqual({
        path: '/versions/v-0/operations?branch=fewer-visits',
        body: { type: 'RemoveVisit', visit_id: 'V-W12' },
      }),
    )

    await userEvent.click(screen.getByTestId('tab-compare'))
    expect(await screen.findByTestId('compare-table')).toBeVisible()
    expect(screen.getByTestId('compare-left')).toHaveValue('main')
    expect(screen.getByTestId('compare-right')).toHaveValue('fewer-visits')

    await userEvent.selectOptions(screen.getByTestId('branch-select'), 'main')
    await waitFor(() => expect(screen.getByTestId('current-branch')).toHaveTextContent('main'))
  })

  it('shows why a branch could not be created', async () => {
    fakeApi()
    render(<App />)
    await userEvent.type(await screen.findByTestId('branch-name'), 'taken')
    await userEvent.click(screen.getByTestId('create-branch'))
    expect(await screen.findByRole('alert')).toHaveTextContent("branch 'taken' already exists")
    expect(screen.getByTestId('current-branch')).toHaveTextContent('main')
  })

  it('reports a study that cannot be loaded', async () => {
    vi.stubGlobal('fetch', () => Promise.resolve(new Response('{"detail":"study not found"}', { status: 404 })))
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load study asthma-ref: study not found')
  })

  it('drafts M11 section 8 and highlights the elements of the sentence that is clicked', async () => {
    const calls = fakeApi()
    render(<App />)
    await userEvent.click(await screen.findByTestId('tab-drafts'))

    expect(await screen.findByTestId('draft-title')).toHaveTextContent(
      '8 Trial Assessments and Procedures',
    )
    expect(calls.some((call) => call.path === '/versions/v-0/drafts')).toBe(true)
    expect(screen.getByTestId('cell-A-SPIRO-V-W12')).toHaveAttribute('data-highlighted', 'false')

    await userEvent.click(screen.getByRole('button', { name: /^Vital signs is performed/ }))
    expect(screen.getByTestId('cell-A-VITALS-V-RAND')).toHaveAttribute('data-highlighted', 'true')
    expect(screen.getByTestId('activity-row-A-VITALS')).toHaveAttribute('data-highlighted', 'true')
    expect(screen.getByTestId('cell-A-SPIRO-V-W12')).toHaveAttribute('data-highlighted', 'false')

    expect(screen.getByTestId('graph-view')).toHaveTextContent('A-VITALS,V-RAND:A-VITALS')

    // Only section 8 is shown with the schedule grid; every section has the graph.
    await userEvent.click(screen.getByTestId('draft-section-5'))
    await userEvent.click(screen.getByRole('button', { name: /^This is a Phase 3 study/ }))
    expect(screen.getByTestId('graph-view')).toHaveTextContent('ARM-DRUG,ARM-PBO')
    expect(screen.queryByTestId('soa-grid')).not.toBeInTheDocument()
  })
})
