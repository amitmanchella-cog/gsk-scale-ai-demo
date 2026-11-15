import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, studyIdFromLocation } from './App'
import { grid, summaries, version } from './fixtures'

// React Flow needs a real layout engine; the graph view is covered by the Playwright suite.
vi.mock('./components/GraphView', () => ({
  GraphView: ({ highlight }: { highlight: ReadonlySet<string> }) => (
    <div data-testid="graph-view">{[...highlight].join(',')}</div>
  ),
}))

/** A tiny in-memory stand-in for csd-api, at the fetch boundary. */
function fakeApi() {
  let head = 'v-0'
  const calls: { path: string; body?: unknown }[] = []
  const respond = (status: number, body: unknown) =>
    Promise.resolve(new Response(JSON.stringify(body), { status }))
  vi.stubGlobal('fetch', (input: string, init?: RequestInit) => {
    const path = input.replace('/api', '')
    const body = init?.body ? JSON.parse(String(init.body)) : undefined
    calls.push({ path, body })
    if (path === '/operation-types') return respond(200, ['MoveVisit', 'ChangeEndpointTiming'])
    if (path.endsWith('/versions')) return respond(200, head === 'v-0' ? summaries.slice(0, 1) : summaries)
    if (path.endsWith('/branches'))
      return respond(200, [{ study_id: 's', name: 'main', base_version_id: null, head_version_id: head }])
    if (path.endsWith('/schedule')) return respond(200, grid)
    if (path.endsWith('/operations')) {
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
      path: '/versions/v-0/operations',
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

  it('reports a study that cannot be loaded', async () => {
    vi.stubGlobal('fetch', () => Promise.resolve(new Response('{"detail":"study not found"}', { status: 404 })))
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load study asthma-ref: study not found')
  })
})
