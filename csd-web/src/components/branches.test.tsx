import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { Branch } from '../api/types'
import { comparison, graph, grid } from '../fixtures'
import { formatDelta } from '../lib/format'
import { BranchPanel } from './BranchPanel'
import { ComparePanel } from './ComparePanel'
import { EndpointsPanel } from './EndpointsPanel'
import { ScheduleGrid } from './ScheduleGrid'
import { ScoreBar } from './ScoreBar'

const NONE = new Set<string>()
const branch = (name: string, head: string): Branch => ({
  study_id: 's',
  name,
  base_version_id: name === 'main' ? null : 'v-0',
  head_version_id: head,
})
const BRANCHES = [branch('main', 'v-0'), branch('fewer-visits', 'v-b'), branch('acq5-primary', 'v-c')]

describe('ScoreBar', () => {
  it('shows the three scores with units', () => {
    render(<ScoreBar score={comparison.left.score} />)
    expect(screen.getByTestId('score-visit_count')).toHaveTextContent(/^7$/)
    expect(screen.getByTestId('score-patient_time_minutes')).toHaveTextContent(/^640 min$/)
    expect(screen.getByTestId('score-cost_proxy')).toHaveTextContent(/^2160$/)
  })

  it('formats signed differences', () => {
    const minutes = (value: number) => `${value} min`
    expect(formatDelta(90, minutes)).toBe('+90 min')
    expect(formatDelta(-90, minutes)).toBe('-90 min')
    expect(formatDelta(0, String)).toBe('0')
  })
})

describe('BranchPanel', () => {
  const setup = (canCreate = true) => {
    const onSelect = vi.fn()
    const onCreate = vi.fn()
    render(
      <BranchPanel
        branches={BRANCHES}
        current="main"
        canCreate={canCreate}
        versionLabel="v2"
        onSelect={onSelect}
        onCreate={onCreate}
      />,
    )
    return { onSelect, onCreate }
  }

  it('switches branch', async () => {
    const { onSelect } = setup()
    expect(screen.getByLabelText('New branch from v2')).toBeVisible()
    await userEvent.selectOptions(screen.getByTestId('branch-select'), 'acq5-primary')
    expect(onSelect).toHaveBeenCalledWith('acq5-primary')
  })

  it('creates a branch with a valid, unused name only', async () => {
    const { onCreate } = setup()
    const name = screen.getByTestId('branch-name')
    const create = screen.getByTestId('create-branch')
    expect(create).toBeDisabled()

    await userEvent.type(name, 'Not OK')
    expect(screen.getByTestId('branch-name-problem')).toHaveTextContent('lower-case')
    expect(create).toBeDisabled()

    await userEvent.clear(name)
    await userEvent.type(name, 'fewer-visits')
    expect(screen.getByTestId('branch-name-problem')).toHaveTextContent('already exists')
    await userEvent.type(name, '{Enter}')
    expect(onCreate).not.toHaveBeenCalled()

    await userEvent.clear(name)
    await userEvent.type(name, 'shorter{Enter}')
    expect(onCreate).toHaveBeenCalledWith('shorter')
    expect(name).toHaveValue('')
  })

  it('cannot create while the study is busy', async () => {
    const { onCreate } = setup(false)
    await userEvent.type(screen.getByTestId('branch-name'), 'shorter{Enter}')
    expect(onCreate).not.toHaveBeenCalled()
  })
})

describe('ComparePanel', () => {
  it('renders both scores side by side, the difference, findings and changes', async () => {
    const compare = vi.fn().mockResolvedValue(comparison)
    render(<ComparePanel branches={BRANCHES} initialRight="main" api={{ compare }} />)
    const table = await screen.findByTestId('compare-table')
    // Left starts on main; right on the first other branch.
    expect(compare).toHaveBeenCalledWith('v-0', 'v-b')
    expect(screen.getByTestId('compare-head-left')).toHaveTextContent('main')
    expect(screen.getByTestId('compare-head-right')).toHaveTextContent('fewer-visits')

    const cells = (key: string) =>
      within(within(table).getByTestId(`compare-row-${key}`))
        .getAllByRole('cell')
        .map((cell) => cell.textContent)
    expect(cells('visit_count')).toEqual(['7', '6', '-1'])
    expect(cells('patient_time_minutes')).toEqual(['640 min', '550 min', '-90 min'])
    expect(cells('cost_proxy')).toEqual(['2160', '1940', '-220'])
    expect(screen.getByTestId('compare-delta-visit_count')).toHaveClass('better')

    expect(screen.getByTestId('compare-findings-left')).toHaveTextContent('0 findings')
    expect(screen.getByTestId('compare-findings-right')).toHaveTextContent('1 finding')
    const changes = screen.getAllByTestId('compare-change')
    expect(changes).toHaveLength(2)
    expect(changes[0]).toHaveTextContent('removed visit: Week 4 V-W4')
  })

  it('compares again when a side changes, and starts on the branch being viewed', async () => {
    const compare = vi.fn().mockResolvedValue({
      ...comparison,
      delta: { visit_count: 1, patient_time_minutes: 0, cost_proxy: 0 },
      changes: [],
    })
    render(<ComparePanel branches={BRANCHES} initialRight="acq5-primary" api={{ compare }} />)
    await screen.findByTestId('compare-table')
    expect(compare).toHaveBeenCalledWith('v-0', 'v-c')
    expect(screen.getByTestId('compare-delta-visit_count')).toHaveTextContent('+1')
    expect(screen.getByTestId('compare-delta-visit_count')).toHaveClass('worse')
    expect(screen.getByTestId('compare-delta-cost_proxy')).not.toHaveClass('better', 'worse')
    expect(screen.getByTestId('compare-no-changes')).toBeVisible()

    await userEvent.selectOptions(screen.getByTestId('compare-left'), 'fewer-visits')
    await waitFor(() => expect(compare).toHaveBeenCalledWith('v-b', 'v-c'))
    await userEvent.selectOptions(screen.getByTestId('compare-right'), 'main')
    await waitFor(() => expect(compare).toHaveBeenCalledWith('v-b', 'v-0'))
  })

  it('shows a failed comparison', async () => {
    const compare = vi.fn().mockRejectedValue(new Error('version not found'))
    render(<ComparePanel branches={BRANCHES.slice(0, 1)} initialRight="main" api={{ compare }} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('version not found')
    expect(screen.queryByTestId('compare-table')).not.toBeInTheDocument()
  })
})

describe('branch operations in the grid and the endpoints panel', () => {
  it('removes a visit', async () => {
    const onOperation = vi.fn()
    render(<ScheduleGrid grid={grid} editable highlight={NONE} onOperation={onOperation} />)
    await userEvent.click(screen.getByRole('button', { name: 'Remove visit Week 12' }))
    expect(onOperation).toHaveBeenCalledWith({ type: 'RemoveVisit', visit_id: 'V-W12' })
  })

  it('offers to make a secondary endpoint primary, not the primary one', async () => {
    const onOperation = vi.fn()
    const fev1 = graph.intent.endpoints[0]!
    const endpoints = [fev1, { ...fev1, id: 'EP-ACQ5', name: 'ACQ-5', level: 'secondary' as const }]
    render(
      <EndpointsPanel endpoints={endpoints} editable highlight={NONE} onOperation={onOperation} />,
    )
    expect(screen.queryByTestId('make-primary-EP-FEV1')).not.toBeInTheDocument()
    await userEvent.click(screen.getByTestId('make-primary-EP-ACQ5'))
    expect(onOperation).toHaveBeenCalledWith({ type: 'ChangePrimaryEndpoint', endpoint_id: 'EP-ACQ5' })
  })
})
